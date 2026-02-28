import sqlite3
import json
from datetime import datetime

class SQLiteManager:
    def __init__(self, db_path="youtube_briefing.db"):
        """
        데이터베이스 연결을 초기화하고, 필요한 테이블이 없으면 생성합니다.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        # 딕셔너리 형태로 결과를 반환받기 위해 row_factory 설정
        self.conn.row_factory = sqlite3.Row 
        self._create_tables()

    def _create_tables(self):
        """
        detail 테이블과 daily 테이블을 생성합니다.
        video_id를 PRIMARY KEY로 지정하여 중복 저장을 데이터베이스 단에서 완벽히 차단합니다.
        """
        with self.conn:
            cursor = self.conn.cursor()
            
            # 개별 영상 분석 테이블 (detail)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detail (
                    video_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    category TEXT,
                    channel TEXT,
                    title TEXT,
                    core_fact TEXT,
                    actionable_insight TEXT,
                    noise_analysis TEXT,
                    score INTEGER,
                    grade TEXT,
                    signal_ratio TEXT,
                    reasoning TEXT,
                    thumbnail_url TEXT,
                    video_url TEXT
                )
            ''')

            # 일간 통합 브리핑 테이블 (daily)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily (
                    date TEXT PRIMARY KEY,
                    investment TEXT,
                    affairs TEXT,
                    science TEXT,
                    insight TEXT,
                    html_body TEXT
                )
            ''')

    def get_processed_video_ids(self):
        """
        이미 처리된 영상의 ID 목록을 반환합니다. (Phase 2에서 중복 수집 필터링에 사용)
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT video_id FROM detail")
        # 결과를 문자열 리스트로 변환하여 반환
        return [row['video_id'] for row in cursor.fetchall()]

    def save_detail_analysis(self, analysis):
        """
        Gemini가 분석한 개별 영상 데이터를 DB에 저장합니다.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 배열이나 객체 형태의 데이터는 JSON 문자열로 직렬화하여 저장
        core_fact_str = json.dumps(analysis.get('core_fact', []), ensure_ascii=False)
        insight_str = json.dumps(analysis.get('actionable_insight', []), ensure_ascii=False)
        noise_str = json.dumps(analysis.get('noise_analysis', []), ensure_ascii=False)
        info_val = analysis.get('information_value', {})

        with self.conn:
            cursor = self.conn.cursor()
            # INSERT OR IGNORE: 만에 하나 중복 ID가 들어오면 에러 없이 무시합니다 (멱등성 확보).
            cursor.execute('''
                INSERT OR IGNORE INTO detail (
                    video_id, date, category, channel, title, 
                    core_fact, actionable_insight, noise_analysis, 
                    score, grade, signal_ratio, reasoning, 
                    thumbnail_url, video_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis['videoId'],
                today,
                analysis['category'],
                analysis['channel'],
                analysis['title'],
                core_fact_str,
                insight_str,
                noise_str,
                info_val.get('score', 0),
                info_val.get('grade', 'N/A'),
                info_val.get('signal_ratio', 'N/A'),
                info_val.get('reasoning', ''),
                analysis['thumbnailUrl'],
                f"https://youtube.com/watch?v={analysis['videoId']}"
            ))
            
            if cursor.rowcount > 0:
                print(f"💾 DB 저장 완료: {analysis['title']}")
            else:
                print(f"⚠️ 이미 DB에 존재하는 데이터입니다 (저장 생략): {analysis['title']}")

    def save_daily_briefing(self, briefing):
        """
        Gemini Pro가 생성한 일간 통합 브리핑 데이터를 DB에 저장합니다.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self.conn:
            cursor = self.conn.cursor()
            # INSERT OR REPLACE: 같은 날짜에 파이프라인을 여러 번 돌리면 최신 브리핑으로 덮어씁니다.
            cursor.execute('''
                INSERT OR REPLACE INTO daily (
                    date, investment, affairs, science, insight, html_body
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                today,
                briefing.get('investment', ''),
                briefing.get('affairs', ''),
                briefing.get('science', ''),
                briefing.get('insight', ''),
                briefing.get('htmlBody', '')
            ))
            print("💾 통합 브리핑 DB 저장 완료.")

    def close(self):
        """DB 연결을 안전하게 종료합니다."""
        self.conn.close()