import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Blogger API 권한 범위 (쓰기 권한 포함)
SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_blogger_service():
    creds = None
    # 이전에 인증한 토큰 정보가 있는지 확인
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 인증 정보가 없거나 유효하지 않으면 새로 인증 진행
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[알림] 토큰 갱신 실패 ({str(e)}). 새로 인증을 진행합니다.")
                creds = None

        if not creds:
            # GCC에서 다운로드한 client_secret.json 경로
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            # 로컬에서 브라우저를 띄워 인증 진행
            creds = flow.run_local_server(port=0)
        
        # 다음 실행을 위해 인증 정보를 token.json에 저장
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('blogger', 'v3', credentials=creds)

def check_blogger_service():
    blog_id = os.getenv('BLOG_ID')
    if not blog_id:
        print("❌ 오류: .env 파일에 BLOG_ID가 설정되지 않았습니다.")
        return

    try:
        service = get_blogger_service()
        print("✅ 확인 완료: Blogger API 서비스 객체가 생성되었습니다.")

        test_thumbnail = 'https://img.youtube.com/vi/0lHFniBCuJw/maxresdefault.jpg'
        html_content = f'''
            <h2>로컬 시스템 연동 테스트</h2>
            <p>이 포스트가 보인다면 Python SDK를 통한 OAuth2 인증에 성공한 것입니다.</p>
            <img src="{test_thumbnail}" style="max-width:100%; border-radius:10px;"/>
            <p>미니 PC(Lubuntu)에서 직접 전송된 데이터입니다.</p>
        '''

        # 포스트 생성 (isDraft=True로 설정하여 초안으로 저장)
        posts = service.posts()
        body = {
            'kind': 'blogger#post',
            'title': '🛠 로컬 파이썬 인증 점검 포스트',
            'content': html_content
        }
        
        request = posts.insert(blogId=blog_id, body=body, isDraft=True)
        result = request.execute()

        print(f"✅ 확인 완료: Blogger 초안 게시물이 성공적으로 생성되었습니다.")
        print(f"🔗 확인용 관리자 URL: https://www.blogger.com/blog/posts/{blog_id}")
        print(f"📄 생성된 포스트 ID: {result.get('id')}")

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == '__main__':
    check_blogger_service()