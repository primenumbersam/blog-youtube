from datetime import datetime
import time
from core_database import SQLiteManager
from api_blogger import BloggerPublisher
from dotenv import load_dotenv

load_dotenv()

def run_publish_test():
    print("[테스트 시작] 로컬 데이터베이스의 오늘자 기록을 바탕으로 출판을 시도합니다.")
    
    db = SQLiteManager()
    publisher = BloggerPublisher()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM detail WHERE date = ?", (today,))
    analyses_rows = cursor.fetchall()
    
    analyses = [dict(row) for row in analyses_rows]
    
    if not analyses:
        print("[알림] 오늘 날짜로 분석되어 저장된 영상 데이터가 없습니다.")
        db.close()
        return

    print(f"[조회 완료] 총 {len(analyses)}개의 영상 데이터를 발행 파이프라인으로 넘깁니다.")
    
    categories = set()
    for i, analysis in enumerate(analyses):
        publisher.publish_video_post(analysis)
        categories.add(analysis.get('category'))
        
        if i < len(analyses) - 1:
            time.sleep(10)
            
    cursor.execute("SELECT * FROM daily WHERE date = ?", (today,))
    briefing_row = cursor.fetchone()
    
    if briefing_row:
        print("[조회 완료] 통합 브리핑 문서를 발행합니다.")
        briefing = dict(briefing_row)
        publisher.publish_briefing_post(briefing, analyses, list(categories))
    else:
        print("[알림] 오늘 날짜의 통합 브리핑 데이터가 데이터베이스에 없습니다.")

    db.close()
    print("[테스트 종료] 데이터베이스 연동 및 블로거 출판 검증이 완료되었습니다.")

if __name__ == "__main__":
    run_publish_test()