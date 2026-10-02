import argparse
import csv
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from core_database import SQLiteManager
from api_youtube import YouTubeAgent
from api_gemini import GeminiAnalyzer
from api_blogger import BloggerPublisher

load_dotenv()

class PipelineOrchestrator:
    def __init__(self, config_path="config.csv"):
        self.config_path = config_path
        self.db = SQLiteManager()
        self.youtube = YouTubeAgent()
        self.gemini = GeminiAnalyzer()
        self.blogger = BloggerPublisher()
        self.config_data = []
        
        self.analysis_model = "gemini-flash-lite-latest"
        self.briefing_model = "gemini-flash-lite-latest"

    def load_config(self):
        print("[1단계] 설정 파일 로드 시작")
        if not os.path.exists(self.config_path):
            print("[오류] 설정 파일이 프로젝트 폴더에 없습니다.")
            return False

        try:
            with open(self.config_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                self.config_data = list(reader)
            print("[완료] 채널 타겟팅 확인")
            return True
        except Exception as e:
            print(f"[오류] 설정 로드 중 예외 발생: {str(e)}")
            return False

    def save_config(self):
        try:
            fieldnames = ['Category', 'Handle', 'FilterCriteria', 'TargetPlaylistID', 'ChannelID', 'UploadsID']
            with open(self.config_path, mode='w', encoding='utf-8-sig', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.config_data)
            print("[완료] 업데이트된 설정 데이터를 CSV 파일에 저장했습니다.")
        except Exception as e:
            print(f"[오류] CSV 저장 중 예외 발생: {str(e)}")

    def run(self, days=1.0, dry_run=False):
        print(f"[Youtube Briefing Local] 파이프라인 가동 (수집 기준: 최근 {days}일 이내)")

        if not self.load_config():
            self.db.close()
            return

        config_updated = self.youtube.fill_missing_ids(self.config_data)
        if config_updated:
            self.save_config()

        print(f"\n[2단계] 유튜브 데이터 수집 시작 (최근 {days}일 기준)")
        all_videos = self.youtube.fetch_videos(self.config_data, days=days)
        
        if not all_videos:
            print(f"[종료] 최근 {days}일 이내에 발행된 새로운 영상이 없습니다.")
            self.db.close()
            return

        print("\n[3단계] 데이터베이스 중복 필터링")
        processed_ids = self.db.get_processed_video_ids()
        new_videos = [v for v in all_videos if v['videoId'] not in processed_ids]
        
        if not new_videos:
            print("[종료] 수집된 영상이 모두 이미 처리되었습니다.")
            self.db.close()
            return
            
        print(f"[완료] 신규 대상 영상 {len(new_videos)}건 확인")
        for v in new_videos:
            print(f"  - [{v.get('category')}] {v.get('title')} ({v.get('videoId')})")

        if dry_run:
            print("\n[안내] 드라이 런(Dry Run) 모드로 실행되어 AI 분석 및 Blogger 발행을 생략합니다.")
            self.db.close()
            return

        print("\n[4단계] 로컬 자막 추출")
        for video in new_videos:
            print(f"[자막 요청] {video['title']}")
            transcript = self.youtube.extract_transcript(video['videoId'])
            video['transcript'] = transcript

        print("\n[5단계] Gemini 데이터 분석 및 DB 저장")
        analyzed_results = []
        for video in new_videos:
            print(f"[분석 요청] {video['title']}")
            analysis = self.gemini.analyze_video(video, self.analysis_model)
            
            if analysis:
                combined_data = {**video, **analysis}
                analyzed_results.append(combined_data)
                self.db.save_detail_analysis(combined_data)
                print("[분석 완료] 정보 가치 평가 완료")
        
        if not analyzed_results:
            print("[종료] 분석에 성공한 데이터가 없어 과정을 생략합니다.")
            self.db.close()
            return

        print("\n[6단계] Gemini 통합 브리핑 생성")
        briefing_data = self.gemini.generate_briefing(analyzed_results, self.briefing_model)
        if briefing_data:
            today_str = datetime.now().strftime("%Y-%m-%d")
            briefing_data['date'] = today_str
            self.db.save_daily_briefing(briefing_data)

        print("\n[7단계] Blogger 출판 진행")
        categories = set()
        for i, analysis in enumerate(analyzed_results):
            self.blogger.publish_video_post(analysis)
            categories.add(analysis.get('category', '미분류'))
            
            if i < len(analyzed_results) - 1:
                time.sleep(10)

        if briefing_data:
            print("\n[8단계] 통합 브리핑 출판 진행")
            self.blogger.publish_briefing_post(briefing_data, analyzed_results, list(categories))

        self.db.close()
        print("\n[Youtube Briefing Local] 파이프라인 전체 프로세스 정상 종료")

def main():
    parser = argparse.ArgumentParser(description="YouTube Briefing 수동 파이프라인 워크플로우")
    parser.add_argument(
        "--days",
        type=float,
        default=1.0,
        help="수집 대상 기간 (일 단위, 기본값: 1.0 = 최근 24시간)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.csv",
        help="채널 설정 CSV 파일 경로 (기본값: config.csv)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="영상 수집 및 DB 중복 필터링까지만 확인하고 분석/발행 생략"
    )
    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(config_path=args.config)
    orchestrator.run(days=args.days, dry_run=args.dry_run)

if __name__ == "__main__":
    main()