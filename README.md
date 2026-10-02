# YouTube Briefing (Local)

A fully automated, local intelligence pipeline designed to extract, analyze, and publish knowledge from video platforms. This project migrates a monolithic Google Apps Script (GAS) architecture to a modular Python ecosystem running on a low-power Lubuntu OS Mini PC.

By executing locally, the system effectively bypasses datacenter IP restrictions imposed by media platforms, ensuring stable extraction of transcripts through residential network routing. It leverages Large Language Models (LLM) based on Information Theory to strictly separate Signal from Noise, ultimately publishing the refined insights to Google Blogger.


## Key Features

- **Local execution & IP bypass** – Avoids datacenter IP blocks by using your local network, so transcripts can be pulled without complex proxy setups.
- **Information‑theory analysis** – Uses the Gemini API to discriminate between objective facts (signal) and subjective opinions, ungrounded predictions or emotional rhetoric (noise).
- **Lightweight infrastructure** – Replaces Google Sheets with SQLite for a robust, single‑file relational database suitable for low‑power always‑on hardware.
- **Modular architecture** – Follows an object‑oriented style with separate components for data collection, LLM analysis, database management and publishing, making maintenance easy.

## System Architecture

The pipeline is implemented as several orchestrated Python modules:

- `config.csv` – a simple CSV file listing target channels, filtering criteria, and categories.
- `core_database.py` – handles the SQLite database; primary keys prevent duplicate processing and store analysis results.
- `api_youtube.py` – talks to the YouTube Data API v3, fetches transcripts and skips live streams or excessively long videos.
- `api_gemini.py` – contains prompt engineering logic and LLM calls, returning structured JSON and generating daily HTML briefings.
- `api_blogger.py` – manages OAuth 2.0 authorization and publishes to Blogger via the REST API with exponential backoff.
- `main_orchestrator.py` – the entry point that coordinates data flow between all modules.

## Google Cloud Console Configuration

The Google Cloud Console (GCC) is used for authorization and quota management:

1. Create a new project.
2. In **Library**, enable the **YouTube Data API v3** and **Blogger API v3**.
3. Configure the **OAuth consent screen**: choose **External** user type and add your Blogger account as a test user.
4. Generate an **API key** for YouTube data access.
5. Create an **OAuth 2.0 Client ID** for a *Desktop* application to allow publishing. Download the JSON and place it at the project root as `client_secret.json`. (Service accounts don’t work with Blogger.)
6. Obtain a **Gemini API key** separately from Google AI Studio.

## Installation and Setup

1. 가상환경 생성 및 활성화:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. 의존성 패키지 설치:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. 프로젝트 루트에 `.env` 파일 설정:
   ```env
   YOUTUBE_API_KEY=your_youtube_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   BLOG_ID=your_blogger_blog_id_here
   ```

## Authorization & Verification

Blogger API 인증 및 연동 상태 점검:
```bash
python api_blogger.py
```
`token.json`이 없거나 만료된 경우 로컬 브라우저가 실행되며 OAuth 인증이 자동 진행됩니다. 인증이 완료되면 점검용 초안(Draft) 포스트가 블로그에 생성됩니다.

YouTube 자막 추출 단독 점검:
```bash
python api_youtube.py
```

## Manual Workflow Execution

원할 때 로컬에서 수동으로 파이프라인을 실행합니다:

```bash
# 기본 실행 (실행 시점 기준 최근 24시간 영상 수집 및 Blogger 발행)
./run.sh

# 기간 옵션 지정 (예: 최근 3일간 영상 대상)
./run.sh --days 3

# 드라이 런 (API 분석/발행 없이 영상 수집 대상 및 DB 중복 필터링 결과만 점검)
./run.sh --days 1 --dry-run
```

## Security notice

**Do not** commit any of the following to a public repo:

- `.env`
- `client_secret.json`
- `token.json`
- `youtube_briefing.db`

Make sure these files are included in your `.gitignore` before the first commit.