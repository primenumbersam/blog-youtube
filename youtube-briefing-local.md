## Youtube Briefing Local 시스템 아키텍처 설계

운영체제 및 스케줄링 설계

루분투 운영체제(Lubuntu OS)의 크론(cron) 데몬을 활용하는 것은 직관적이고 안정적인 방법입니다. 리눅스(Linux) 환경의 크론은 추가적인 백그라운드 프로세스 매니저 없이도 정해진 시간에 Python 스크립트를 정확히 기동합니다. 미니 피시의 저전력 특성과 결합되어 상시 구동 서버로서의 역할을 충실히 수행할 것입니다.

클라우드 인프라 분리 전략

구글 클라우드 콘솔(Google Cloud Console, GCC)에서 새로운 프로젝트를 생성하여 환경을 분리하는 것은 자원 격리와 할당량(Quota) 관리 측면에서 아주 바람직합니다. 유튜브 데이터 어플리케이션 프로그래밍 인터페이스(YouTube Data API)와 제미나이(Gemini) API 키를 별도로 발급받아 관리하면, 기존 프로젝트와의 간섭 없이 안정적인 운영이 가능합니다.

데이터베이스 마이그레이션

구글 시트(Google Sheets)를 에스큐엘라이트(SQLite)로 대체하는 것은 데이터 파이프라인의 입출력 속도와 안정성을 비약적으로 상승시킵니다. SQLite는 파이썬 표준 라이브러리에 내장되어 있어 별도의 서버 설정이 필요 없는 경량 관계형 데이터베이스(RDBMS)입니다. 대규모 언어 모델(Large Language Model, LLM)이 반환하는 제이슨(JavaScript Object Notation, JSON) 응답 객체와 썸네일(Thumbnail) 주소를 텍스트 형태로 무한정 적재하더라도 단일 파일 기반이므로 관리와 백업이 매우 용이합니다.

데이터 가공 및 출판 파이프라인

메모리에 적재된 LLM의 응답 객체를 곧바로 SQLite에 기록하고, 하이퍼텍스트 마크업 언어(HTML) 템플릿 엔진을 통해 블로거(Blogger) 규격에 맞게 포장합니다. 출판 과정은 구글에서 공식 지원하는 파이썬용 구글 에이피아이 클라이언트 라이브러리(google-api-python-client) 소프트웨어 개발 키트(Software Development Kit, SDK)를 활용하여 REST API 통신을 안전하고 직관적으로 처리할 수 있습니다.

## GCC (Google Cloud Console) 환경 설정

새로 프로젝트 생성 (예: `Youtube Briefing Local`)

### GCC(Google Cloud Console)의 역할과 데이터 흐름

`Youtube Briefing Local` 프로젝트에서 GCC는 일종의 *출입 통제 센터'이자 '권한 위임 대행소'입니다.

| **단계** | **수행 작업** | **GCC 및 자격 증명의 역할** |
| --- | --- | --- |
| **1. 수집** | YouTube에서 영상 데이터(제목, 설명, 조회수 등) 조회 | **YouTube API Key**: 구글 서버에 "내가 정당한 개발자이고, 이 프로젝트의 할당량(Quota) 내에서 데이터를 읽겠다"고 인증하는 용도입니다. |
| **2. 가공** | Gemini에게 텍스트 분석 및 요약 요청 | **Gemini API Key**: Google AI Studio에서 발급받은 키로, 제미나이 모델 사용료 및 사용량을 관리합니다. (GCC와 별개로 작동 가능) |
| **3. 저장** | 로컬 SQLite DB에 결과물 저장 | **자체 엔진**: 구글 클라우드와 무관하게 로컬 미니 PC 자원만 사용합니다. |
| **4. 발행** | 가공된 텍스트를 내 Blogger 계정에 포스팅 | **OAuth 2.0 Client ID**: 가장 중요한 부분입니다. API Key는 단순히 '읽기'는 가능하지만, 남의(혹은 본인의) 블로그에 글을 '쓰는' 행위는 보안상 키 하나로 허용되지 않습니다. "내 계정의 블로그 쓰기 권한을 이 로컬 앱에 위임한다"는 사용자 승인이 필요하며, GCC는 이 인증 프로세스를 중개합니다.
`` |
- **Quota 관리**: GCC는 당신의 앱이 하루에 유튜브 데이터를 얼마나 조회하는지 감시하고 제한합니다. 무료 티어의 한도를 넘지 않게 관리하는 대시보드 역할을 합니다.
- **Blogger 쓰기 권한**: 블로거에 포스팅할 때, 구글 서버는 "이 요청이 Sam(사용자) 본인이 보낸 게 맞나?"를 확인해야 합니다. OAuth 2.0 클라이언트 ID를 통해 최초 1회 로그인을 수행하면 `token.json` 같은 파일이 로컬에 생성되는데, 이후에는 이 파일이 '출입증' 역할을 하여 자동으로 포스팅이 가능해집니다.
- **데이터센터 IP 차단 우회**: 이게 로컬 버전의 핵심입니다. GCC 설정은 클라우드와 동일하지만, 실제 '패킷(Packet)'을 쏘는 지점이 구글 데이터센터가 아닌 당신의 집(Mini PC)이기 때문에 유튜브 자막 추출 서버가 당신을 '일반 사용자'로 오해하게 만드는 전략입니다.

### 필수 API 활성화 (Enable APIs)

1. GCC 좌측 햄버거 메뉴에서 **APIs & Services > Library**로 이동합니다.
2. `YouTube Data API v3`를 검색하여 **Enable(사용 설정)** 합니다.
3. `Blogger API v3`를 검색하여 **Enable(사용 설정)** 합니다.


### 앱의 신원 정의: OAuth 동의 화면 구성 (OAuth Consent Screen)

자격 증명을 만들기 전, 앱의 신원을 정의하는 과정입니다.

1. **APIs & Services > OAuth consent screen**으로 이동합니다.
2. User Type은 **External(외부)**로 선택하고 Create를 누릅니다.
3. App name (예: Youtube Local), User support email, Developer contact email 등 필수 항목만 채웁니다.
4. **Scopes(범위)** 단계는 과감히 건너뜁니다 (코드에서 동적으로 요청할 것입니다).
5. **Test users(테스트 사용자)** 단계에서 본인의 구글 계정(Blogger를 운영하는 계정)을 반드시 추가합니다. (앱을 퍼블리싱하지 않고 테스트 모드로 평생 쓸 것이기 때문입니다.)

### 자격 증명 생성 (Credentials)

이 부분이 로컬 오케스트레이션의 핵심입니다.

- **API Key:** YouTube 데이터 수집 시 읽기 전용으로만 쓸 때 편리합니다. **Create Credentials > API key**를 눌러 생성하고 (Youtube, Gemini), Key를 로컬의 `.env` 파일에 저장. *참고: Gemini API는 Google AI Studio에서 별도로 키를 발급받는 것이 무료 할당량 및 모델 접근성 면에서 로컬 프로젝트에 훨씬 유리합니다.*
- **OAuth 2.0 Client IDs (필수):** Blogger에 글을 '게시(Write)'하려면 사용자 인증이 필요합니다.
    1. **Create Credentials > OAuth client ID**를 클릭합니다.
    2. Application type을 Desktop app(데스크톱 앱)으로 선택합니다. (Web application이 아닙니다.)
    3. 이름을 지정하고 생성합니다.
    4. 생성 완료 후 목록 우측의 다운로드 아이콘을 눌러 제이슨(JSON) 파일을 다운로드합니다. 이 파일을 로컬 PC의 프로젝트 폴더 안에 `client_secret.json`이라는 이름으로 저장해 둡니다.

**팁: 왜 Service Account(서비스 계정)는 쓰지 않나요?**

서비스 계정은 서버 대 서버 통신에 완벽하지만, **Blogger API와는 궁합이 최악입니다.** 서비스 계정은 자체적인 가상 이메일을 가지는데, Blogger 시스템은 이 가상 이메일을 블로그 관리자로 쉽게 초대하거나 권한을 부여할 수 **없도록** 설계되어 있습니다. 따라서 로컬 데스크톱 앱 방식의 OAuth 2.0을 사용하여 최초 1회만 브라우저로 로그인(인가)하고, 발급된 Refresh Token을 로컬에 저장하여 영구적으로 재사용하는 방식이 가장 견고합니다.

## Local Workspace에서 준비 환경 설정 (Lubuntu OS)

### Local venv & Dependency
이제 `blog-youtube` 폴더에서 작업을 시작할 차례입니다. 루분투 미니 PC의 터미널에서 아래 명령어를 실행하여 파이썬 가상 환경을 구축하십시오.

```bash
# 1. 폴더 이동
cd ~/blog-youtube

# 2. 가상환경 생성 (python3-venv 패키지가 필요할 수 있음)
python3 -m venv .venv

# 3. 가상환경 활성화
source .venv/bin/activate

# 4. 필수 라이브러리 설치
pip install --upgrade google-api-python-client google-auth-oauthlib google-auth-httplib2 google-generativeai youtube-transcript-api python-dotenv

```

### Local Test: OAuth 인증을 통해 Blogger 쓰기 권한(Token)을 확보하는 스크립트 (test_auth.py)
구글 앱스 스크립트(GAS)에서는 ScriptApp.getOAuthToken()이 백그라운드에서 자동으로 처리해주었지만, 로컬 파이썬 환경에서는 우리가 직접 사용자 인가(Authorization) 과정을 거쳐야 합니다. 이 과정이 끝나면 로컬 폴더에 token.json 파일이 생성되며, 이후에는 비밀번호 입력 없이도 24시간 자동화 구동이 가능해집니다 (최초 1회).

이 스크립트는 두 가지 역할을 합니다.

1. 브라우저를 띄워 본인의 구글 계정 로그인을 요청하고 Blogger 쓰기 권한을 확보합니다.
2. 확보된 권한으로 초안(Draft) 게시물을 하나 생성하여 실제 쓰기 기능이 작동하는지 검증합니다.

```Bash
python test_auth.py
```

## Local System 설계도

기존 구글 앱스 스크립트(Google Apps Script, GAS) 기반의 모놀리식(Monolithic) 코드를 파이썬(Python)의 객체 지향적이고 모듈화된 아키텍처로 재설계합니다.

## Youtube Briefing Local 시스템 아키텍처 설계

Incremental Integration 방식으로 개발을 진행합니다.

기존 스프레드시트(Spreadsheet) 기반의 설정 파일을 대체할 포맷으로는 콤마 분리 변수(Comma Separated Values, CSV)를 사용합니다. 제이슨(JavaScript Object Notation, JSON)이나 야믈(YAML Ain't Markup Language, YAML)은 계층적 구조를 표현하기 좋지만, 우리가 관리할 채널 설정(카테고리, 핸들, 플레이리스트 ID 등)은 완벽한 2차원 표 형태를 띠고 있습니다. CSV는 엑셀(Excel)이나 맥용 넘버스(Numbers)에서 기존 구글 시트(Google Sheets)와 동일한 사용자 경험으로 직관적인 수정이 가능하며, 파이썬 표준 라이브러리로 가볍게 읽어 들일 수 있습니다.

데이터 저장소는 에스큐엘라이트(SQLite)를 사용합니다. 관계형 데이터베이스(Relational Database, RDB)의 구조적 무결성과 단일 파일 기반의 편리함이 겹치는 지점에 위치하여, 미니 피시(Mini PC) 환경에 최적화된 영구 저장소 역할을 수행할 것입니다.

### 로컬 디렉토리 및 파일 구조

프로젝트 폴더 내부는 각 역할에 따라 독립적인 파이썬 스크립트 파일로 분할됩니다.

* .env
* client_secret.json
* config.csv
* core_database.py
* api_youtube.py
* api_gemini.py
* api_blogger.py
* main_orchestrator.py

### 환경 설정 데이터 모델 (config.csv)

헤더 행을 포함하여 기존 Config 시트의 열 구조를 그대로 이관합니다. 프로그램 실행 시 메모리에 딕셔너리(Dictionary) 리스트 형태로 로드되어 각 모듈에 주입됩니다.

* Category
* ChannelHandle
* Criteria
* TargetPlaylistId
* ChannelId
* UploadsId

### 데이터베이스 관리 모듈 (core_database.py)

SQLite 데이터베이스와의 세션(Session) 연결 및 테이블(Table) 스키마 생성을 담당하는 SQLiteManager 클래스를 설계합니다. 기존 `4-storage-publish.gs`의 시트 기록 역할을 대체합니다.

* 테이블 초기화 기능: 프로그램 최초 실행 시 detail 테이블과 daily 테이블이 존재하지 않으면 자동으로 생성합니다. detail 테이블에는 고유 식별자(Video ID)를 기본 키(Primary Key)로 설정하여 데이터 중복 적재를 원천적으로 차단합니다.
* 중복 검증 기능: 메인 로직이 호출할 수 있도록 기존에 처리 완료된 Video ID 목록을 리스트 형태로 반환합니다.
* 데이터 적재 기능: 대규모 언어 모델(Large Language Model, LLM)의 응답 제이슨 객체를 문자열로 직렬화(Serialization)하여 저장합니다. 썸네일(Thumbnail)과 비디오 주소(URL)도 텍스트 형태로 함께 보관합니다.

### 유튜브 데이터 수집 모듈 (api_youtube.py)

어플리케이션 프로그래밍 인터페이스(Application Programming Interface, API) 통신과 자막 추출을 전담하는 YouTubeAgent 클래스를 설계합니다. 기존 `2-youtube-api.gs` 로직과 `youtube-transcript-api` 모듈을 결합합니다.

* 최신 영상 검색 기능: CSV에서 기준(Criteria)이 newest인 채널의 재생목록을 조회하여 24시간 이내의 영상을 필터링합니다.
* 최고 조회수 검색 기능: 기준이 most viewed인 채널의 최근 10개 영상을 조회하여 24시간 이내 조회수 1위 영상을 판별합니다.
* 자막 추출 기능: 전달받은 Video ID를 바탕으로 한국어 자막을 우선 추출하고, 없을 경우 설명(Description) 텍스트를 반환하도록 예외 처리를 캡슐화(Encapsulation)합니다.

### 제미나이 언어 모델 모듈 (api_gemini.py)

구글 인공지능 스튜디오(Google AI Studio)의 SDK를 활용하여 텍스트 분석과 요약을 수행하는 GeminiAnalyzer 클래스를 설계합니다. 기존 `3-gemini-ai.gs`를 대체합니다.

* 프롬프트 템플릿 관리: 카테고리(Investment, Affairs, Popular Science)에 따른 시스템 프롬프트(System Prompt)를 내장합니다.
* 구조화된 분석 요청 기능: flash-lite 모델을 호출하여 신호(Signal)와 소음(Noise)을 분리하고, 지정된 4차원 스키마에 맞춘 제이슨 객체를 반환받습니다.
* 통합 브리핑 생성 기능: pro 모델을 호출하여 개별 분석된 결과물들을 종합하고, 블로그 게시용 하이퍼텍스트 마크업 언어(HTML) 본문을 작성합니다.

### 블로거 출판 모듈 (api_blogger.py)

앞서 테스트한 OAuth 2.0 인증 로직(`test_auth.py`)을 바탕으로 실제 포스트를 발행하는 BloggerPublisher 클래스를 설계합니다.

* 권한 검증 기능: 초기화 시 로컬의 token.json을 확인하고, 만료되었을 경우 자동으로 리프레시 토큰(Refresh Token)을 사용해 갱신합니다.
* 개별 포스트 발행 기능: GeminiAnalyzer가 가공한 데이터를 HTML로 포장하여 카테고리 태그와 함께 발행합니다.
* 브리핑 포스트 발행 기능: 매일 생성되는 통합 브리핑 문서를 썸네일 갤러리와 결합하여 발행합니다. 속도 제한(Rate Limit)에 대응하기 위해 내부적으로 지수 백오프(Exponential Backoff) 로직을 포함합니다.

### 메인 오케스트레이터 (main_orchestrator.py)

개별적으로 설계된 클래스들을 인스턴스화(Instantiation)하고 데이터의 흐름을 통제하는 PipelineOrchestrator 클래스를 구성합니다.

* CSV 설정을 로드하고 DB 매니저를 연결합니다.
* 유튜브 에이전트를 통해 영상을 수집하고, DB 매니저를 통해 중복을 제거합니다.
* 제미나이 아날라이저에 분석을 의뢰하고, 그 결과를 DB에 저장합니다.
* 블로거 퍼블리셔에 결과물을 전달하여 최종 발행을 마무리합니다.
* 루분투(Lubuntu) OS의 크론(cron) 데몬이 이 파일을 직접 실행하게 됩니다.

## Lubuntu OS에서 Cronjob 등록 절차

크론잡을 설정할 때는 모든 경로를 절대 경로로 명시하고, 실행 전 프로젝트 폴더로 이동하는 작업이 필수적입니다. 작업 공간을 /home/sam/github/blog-youtube 로 가정하고 설명합니다. 실제 경로가 다르다면 본인의 경로에 맞게 수정하십시오.

크론 탭 편집기 실행, 실행 스케줄 및 명령어 등록
터미널을 열고 아래 명령어를 입력하여 크론 스케줄링 편집기를 호출합니다. 처음 실행할 경우 편집기(nano 또는 vim)를 선택하라는 메시지가 나올 수 있으며, 사용이 편한 편집기를 선택하시면 됩니다. 

```bash
crontab -e
```

파일의 가장 하단으로 이동하여 아래의 명령어를 한 줄로 입력합니다. 이 명령어는 매일 오전 10시 정각에 폴더로 이동한 뒤, 가상 환경 내부에 있는 파이썬 실행 파일을 사용하여 메인 오케스트레이터를 가동하고, 그 결과를 로그 파일로 남기라는 의미입니다.

```text
0 10 * * * cd /home/sam/github/blog-youtube && /home/sam/github/blog-youtube/.venv/bin/python main_orchestrator.py >> /home/sam/github/blog-youtube/cron_log.txt 2>&1
```

설정 저장 및 데몬 반영
입력 후 파일을 저장하고 종료합니다. 터미널에 crontab: installing new crontab 이라는 메시지가 출력되었다면 예약이 시스템에 정상적으로 각인된 것입니다.

이로써 클라우드 플랫폼의 제약에서 벗어나, 독립적인 자원으로 지식 파이프라인을 운영하는 시스템 구축이 완료되었습니다. 지정된 시간이 지난 후 cron_log.txt 파일을 열어보시면 자동화 시스템이 남긴 발자취를 확인하실 수 있습니다.

## github 공개 절차

```bash
git init
git add .
git commit -m "Initial commit: Establish local Youtube Briefing pipeline"

# GitHub에 접속하여 blog-youtube라는 이름으로 새로운 퍼블릭 저장소를 생성한 다음

git branch -M main
git remote add origin https://github.com/primenumbersam/blog-youtube.git
git push -u origin main

```