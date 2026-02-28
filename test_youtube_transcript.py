from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

def test_extract_transcript(video_id):
    print("로컬 자막 추출 테스트를 시작합니다.")
    
    try:
        # 인스턴스 생성 후 fetch 메서드 사용, 한국어('ko') 명시
        ytt_api = YouTubeTranscriptApi()
        
        # 여기서 유튜브 서버가 로컬 IP의 요청을 허용하고 자막을 내려줍니다.
        transcript_data = ytt_api.fetch(video_id, languages=['ko', 'en'])
        
        # 타임스탬프를 제거하고 순수 텍스트로 결합
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript_data)
        
        print("✅ 자막 추출 성공. 내용 미리보기:")
        print(text_formatted[:] + "...")
        
        return text_formatted

    except Exception as e:
        print("❌ 자막 추출 중 오류가 발생했습니다: " + str(e))
        return None

if __name__ == "__main__":
    target_video_id = "SUpRFwsjtBM"
    test_extract_transcript(target_video_id)