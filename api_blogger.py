import os
import json
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class BloggerPublisher:
    def __init__(self):
        self.blog_id = os.getenv('BLOG_ID')
        if not self.blog_id:
            print("[경고] .env 파일에 BLOG_ID가 설정되지 않았습니다.")
        
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/blogger'])
        else:
            print("[오류] token.json 파일이 없습니다. auth_test.py를 실행하여 권한을 확보하십시오.")
            
        self.service = build('blogger', 'v3', credentials=creds)

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
            core_facts = json.loads(analysis.get('core_fact', '[]'))
            insights = json.loads(analysis.get('actionable_insight', '[]'))
            
            html_content = (
                f'<div style="text-align:center;margin-bottom:20px;">'
                f'<img src="{analysis.get("thumbnail_url", "")}" alt="thumbnail" style="max-width:100%;border-radius:8px;"/></div>'
                f'<h3>핵심 사실 (Core Facts)</h3><ul>'
                + ''.join([f'<li>{f}</li>' for f in core_facts]) +
                f'</ul><h3>시사점 (Actionable Insights)</h3><ul>'
                + ''.join([f'<li>{i}</li>' for i in insights]) +
                f'</ul><h3>정보 가치 평가 (Evaluation)</h3>'
                f'<p>{analysis.get("grade", "N/A")} ({analysis.get("score", 0)}/100) | 신호 비율: {analysis.get("signal_ratio", "N/A")}</p>'
                f'<p>{analysis.get("reasoning", "")}</p>'
                f'<p><a href="{analysis.get("video_url", "")}">원본 영상 보기</a></p>'
            )

            body = {
                'kind': 'blogger#post',
                'blog': {'id': self.blog_id},
                'title': analysis.get('title', '제목 없음'),
                'content': html_content,
                'labels': [analysis.get('category', '미분류')]
            }

            request = self.service.posts().insert(blogId=self.blog_id, body=body, isDraft=False)
            self._fetch_with_backoff(request)
            print(f"[발행 완료] {analysis.get('title')}")
        except Exception as e:
            print(f"[발행 실패] {analysis.get('title')}: {str(e)}")

    def publish_briefing_post(self, briefing, analyses, categories):
        try:
            today = briefing.get('date', '')
            gallery = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">'
            
            for a in analyses:
                gallery += (
                    f'<a href="{a.get("video_url", "")}">'
                    f'<img src="{a.get("thumbnail_url", "")}" alt="thumbnail" style="width:180px;border-radius:6px;"/></a>'
                )
            gallery += '</div>'

            html_content = gallery + briefing.get('html_body', '')

            body = {
                'kind': 'blogger#post',
                'blog': {'id': self.blog_id},
                'title': f'{today} 일간 미디어 브리핑',
                'content': html_content,
                'labels': categories
            }

            request = self.service.posts().insert(blogId=self.blog_id, body=body, isDraft=False)
            self._fetch_with_backoff(request)
            print("[통합 브리핑 발행 완료]")
        except Exception as e:
            print(f"[통합 브리핑 발행 실패] {str(e)}")