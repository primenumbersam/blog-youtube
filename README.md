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

1. Clone the repository and create a virtual environment:
   ```bash
   cd ~/github/blog-youtube
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install required packages:
   ```bash
   pip install --upgrade \
     google-api-python-client \
     google-auth-oauthlib \
     google-auth-httplib2 \
     google-generativeai \
     youtube-transcript-api \
     python-dotenv
   ```
3. Create a `.env` file in the project root with the following variables:
   ```env
   YOUTUBE_API_KEY=your_youtube_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   BLOG_ID=your_blogger_blog_id_here
   ```

## Initial Authorization

Grant the necessary Blogger publishing permissions by running:
```bash
python test_auth.py
```
A `token.json` file will be created in the project root, enabling the script to run unattended thereafter.

## Automation via cron

To run the orchestrator daily, add a cron entry:
```bash
crontab -e
```
Then append (adjust the time/path as needed):
```cron
0 10 * * * cd /home/sam/github/blog-youtube && \
  /home/sam/github/blog-youtube/.venv/bin/python main_orchestrator.py \
  >> /home/sam/github/blog-youtube/cron_log.txt 2>&1
```
Ensure you use absolute paths.

## Security notice

**Do not** commit any of the following to a public repo:

- `.env`
- `client_secret.json`
- `token.json`
- `youtube_briefing.db`

Make sure these files are included in your `.gitignore` before the first commit.