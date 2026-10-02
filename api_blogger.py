import os
import json
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

class BloggerPublisher:
    SCOPES = ['https://www.googleapis.com/auth/blogger']

    def __init__(self, token_path='token.json', client_secret_path='client_secret.json'):
        self.blog_id = os.getenv('BLOG_ID')
        self.token_path = token_path
        self.client_secret_path = client_secret_path
        if not self.blog_id:
            print("[경고] .env 파일에 BLOG_ID가 설정되지 않았습니다.")
        
        creds = self._get_credentials()
        self.service = build('blogger', 'v3', credentials=creds)

    def _get_credentials(self):
        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except Exception as e:
                print(f"[경고] token.json 읽기 실패: {str(e)}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("[알림] Blogger API 토큰이 만료되었습니다. 갱신을 시도합니다...")
                    creds.refresh(Request())
                    with open(self.token_path, 'w', encoding='utf-8') as token_file:
                        token_file.write(creds.to_json())
                    print("[완료] 토큰이 성공적으로 갱신되었습니다.")
                    return creds
                except Exception as e:
                    print(f"[오류] 토큰 갱신 실패: {str(e)}. 새로 인증을 시도합니다.")
                    creds = None

            if not creds:
                if not os.path.exists(self.client_secret_path):
                    raise FileNotFoundError(
                        f"[오류] {self.client_secret_path} 파일이 없습니다. Google Cloud Console에서 OAuth 클라이언트 시크릿을 다운로드하세요."
                    )
                print("[알림] 브라우저를 통해 Blogger OAuth 인증을 진행합니다...")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
                with open(self.token_path, 'w', encoding='utf-8') as token_file:
                    token_file.write(creds.to_json())
                print(f"[완료] 새 인증 토큰을 {self.token_path}에 저장했습니다.")

        return creds

    def _fetch_with_backoff(self, request, max_retries=3):
        retries = 0
        delay = 5
        
        while retries <= max_retries:
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status in [403, 429, 500, 503]:
                    if retries == max_retries:
                        print("[오류] API 최대 재시도 횟수를 초과했습니다.")
                        raise e
                    print(f"[지연] API 호출 제한 감지. {delay}초 후 재시도합니다.")
                    time.sleep(delay)
                    retries += 1
                    delay *= 2
                else:
                    raise e
    
    def publish_video_post(self, analysis):
        try:
            # 메모리에서 온 List인지, DB에서 온 String인지 판별하여 유연하게 처리합니다.
            def parse_json_field(field):
                if isinstance(field, (list, dict)):
                    return field
                if isinstance(field, str):
                    try:
                        return json.loads(field)
                    except (json.JSONDecodeError, TypeError):
                        return [field] if field else []
                return []

            core_facts = parse_json_field(analysis.get('core_fact', []))
            insights = parse_json_field(analysis.get('actionable_insight', []))
            
            info_val = analysis.get('information_value')
            if info_val is None:
                grade = analysis.get("grade", "N/A")
                score = analysis.get("score", 0)
                signal_ratio = analysis.get("signal_ratio", "N/A")
                reasoning = analysis.get("reasoning", "")
            else:
                grade = info_val.get("grade", "N/A")
                score = info_val.get("score", 0)
                signal_ratio = info_val.get("signal_ratio", "N/A")
                reasoning = info_val.get("reasoning", "")
            
            html_content = (
                f'<div style="text-align:center;margin-bottom:20px;">'
                f'<img src="{analysis.get("thumbnailUrl", analysis.get("thumbnail_url", ""))}" alt="thumbnail" style="max-width:100%;border-radius:8px;"/></div>'
                f'<h3>핵심 사실 (Core Facts)</h3><ul>'
                + ''.join([f'<li>{f}</li>' for f in core_facts]) +
                f'</ul><h3>시사점 (Actionable Insights)</h3><ul>'
                + ''.join([f'<li>{i}</li>' for i in insights]) +
                f'</ul><h3>정보 가치 평가 (Evaluation)</h3>'
                f'<p>{grade} ({score}/100) | 신호 비율: {signal_ratio}</p>'
                f'<p>{reasoning}</p>'
                f'<p><a href="{analysis.get("video_url", f"https://youtube.com/watch?v={analysis.get("videoId", "")}")}">원본 영상 보기</a></p>'
            )

            raw_title = analysis.get('title', '제목 없음')
            channel = analysis.get('channel', '')
            post_title = f"[{channel}] {raw_title}" if channel else raw_title

            body = {
                'kind': 'blogger#post',
                'blog': {'id': self.blog_id},
                'title': post_title,
                'content': html_content,
                'labels': [analysis.get('category', '미분류')]
            }

            request = self.service.posts().insert(blogId=self.blog_id, body=body, isDraft=False)
            self._fetch_with_backoff(request)
            print(f"  [발행 완료] {analysis.get('title')}")
        except Exception as e:
            print(f"  [발행 실패] {analysis.get('title')}: {str(e)}")

    def publish_briefing_post(self, briefing, analyses, categories):
        try:
            today = briefing.get('date', '')
            gallery = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">'
            
            for a in analyses:
                video_url = a.get("video_url", f"https://youtube.com/watch?v={a.get('videoId', '')}")
                thumbnail_link = a.get("thumbnailUrl", a.get("thumbnail_url", ""))
                gallery += (
                    f'<a href="{video_url}">'
                    f'<img src="{thumbnail_link}" alt="thumbnail" style="width:180px;border-radius:6px;"/></a>'
                )
            gallery += '</div>'

            html_content = gallery + briefing.get('htmlBody', briefing.get('html_body', ''))

            body = {
                'kind': 'blogger#post',
                'blog': {'id': self.blog_id},
                'title': f'{today} 브리핑',
                'content': html_content,
                'labels': categories
            }

            request = self.service.posts().insert(blogId=self.blog_id, body=body, isDraft=False)
            self._fetch_with_backoff(request)
            print("[통합 브리핑 발행 완료]")
        except Exception as e:
            print(f"[통합 브리핑 발행 실패] {str(e)}")

    def check_connection(self, is_draft=True):
        """Blogger API 연동 및 권한을 점검하는 테스트 포스트를 발행합니다."""
        if not self.blog_id:
            print("[오류] BLOG_ID가 설정되지 않았습니다.")
            return False

        try:
            body = {
                'kind': 'blogger#post',
                'title': '🛠 Blogger 연동 점검 포스트',
                'content': '<p>Blogger API 연동이 정상 작동 중입니다.</p>'
            }
            request = self.service.posts().insert(blogId=self.blog_id, body=body, isDraft=is_draft)
            result = request.execute()
            status_text = "초안(Draft)" if is_draft else "발행"
            print(f"[성공] Blogger {status_text} 포스트 생성 완료 (ID: {result.get('id')})")
            return True
        except Exception as e:
            print(f"[오류] Blogger 연동 점검 실패: {str(e)}")
            return False

if __name__ == '__main__':
    publisher = BloggerPublisher()
    publisher.check_connection(is_draft=True)