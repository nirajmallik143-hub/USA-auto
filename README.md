# USA Kids Automated Video Production & YouTube Upload Pipeline

A high-volume, automated Python-based video generation and publishing pipeline designed to produce and publish **5 vertical YouTube Shorts (9:16)** and **2 horizontal long-form videos (16:9)** daily targeting US kids' content.

Built with strict **COPPA compliance**, resilient job queueing with automatic retries, LLM-powered scriptwriting with procedural offline fallbacks, kid-friendly voiceovers and visual asset generation, and automated YouTube Data API v3 publishing.

---

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Daily Schedule & Quota Matrix](#daily-schedule--quota-matrix)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Prerequisites & Installation](#prerequisites--installation)
- [Environment Configuration](#environment-configuration)
- [CLI Usage Guide](#cli-usage-guide)
- [Running the Scheduler](#running-the-scheduler)
  - [Option 1: Standalone APScheduler (Local / VM)](#option-1-standalone-apscheduler-local--vm)
  - [Option 2: Celery + Redis (Distributed Cloud)](#option-2-celery--redis-distributed-cloud)
  - [Option 3: Docker & Docker Compose](#option-3-docker--docker-compose)
- [GitHub Actions Automation](#github-actions-automation-fully-automated-uploads)
- [COPPA & Child Safety Compliance](#coppa--child-safety-compliance)
- [Testing & Quality Assurance](#testing--quality-assurance)

---

## Architecture Overview

```
                                      +------------------------+
                                      | Daily Scheduler / Cron |
                                      | (APScheduler / Celery) |
                                      +-----------+------------+
                                                  |
                                                  v
                                      +------------------------+
                                      |     Queue Manager      |
                                      | (Retry & Quota Engine) |
                                      +-----------+------------+
                                                  |
           +--------------------------------------+--------------------------------------+
           |                                      |                                      |
           v                                      v                                      v
+---------------------+                +---------------------+                +---------------------+
| Content Generation  |                | Production Pipeline |                | YouTube API v3      |
|                     |                |                     |                |                     |
| • Topic Rotator     |                | • ElevenLabs / gTTS |                | • OAuth / Mock Client|
| • LLM Script Engine | -------------> | • Kid Visuals Engine| -------------> | • COPPA Compliance  |
| • Timing & Words    |                | • Audio & Chimes    |                | • SEO Tags & Desc   |
| • Safety Prompts    |                | • Subtitles Overlay |                | • Scheduled Upload  |
+---------------------+                | • MoviePy & FFmpeg  |                +---------------------+
                                       +---------------------+
                                                  |
                                                  v
                                      +------------------------+
                                      | SQLite State Manager   |
                                      | (Jobs, Retries, Logs)  |
                                      +------------------------+
```

### 1. High-Volume Scheduling & Queue Manager
- **7 Daily Slots**: Strict separation into 5 Shorts (<60s) and 2 Long-form (3–8 min) videos paced throughout the US daytime.
- **State Tracking & Quota Manager**: Tracks all video jobs in SQLite (`output/pipeline.db`). Prevents duplicate runs, preserves daily quotas (`5 Shorts + 2 Long`), and protects against runaway generation.
- **Automatic Retry Engine**: Failed jobs automatically retry up to `MAX_RETRIES` (default: 3) with exponential backoff without resetting or disturbing completed slots.

### 2. Content Generation Engine
- **Topic Rotation**: Rotates through seven high-engagement US kids' themes:
  - *Animal Riddles*
  - *Moral Stories & Kindness Tales*
  - *Alphabet & Number Learning*
  - *Space Exploration & Solar System Facts*
  - *Dinosaur Adventures*
  - *Fun Science Curiosities*
  - *Kids' Jokes & Brain Puzzles*
- **Dynamic Script Generation**: Supports OpenAI (`gpt-4o-mini`, `gpt-4o`) and Anthropic (`claude-3-5-sonnet`) with prompt templates calibrated for vocabulary, target durations (Shorts: 80–120 words; Long: 450–900 words), and scene pacing.
- **Zero-Dependency Procedural Fallback Engine**: When API keys are not supplied, the built-in procedural engine creates complete, structured, pedagogically sound scripts offline.

### 3. Production Pipeline (Voice, Visuals, Assembly)
- **Kid-Friendly Voiceover Engine**: ElevenLabs integration with cheerful kid voices (e.g., *Rachel*, *Domi*) and gTTS (Google Text-to-Speech) fallback.
- **Visuals Engine**:
  - Automatically fetches curated, safe stock footage via Pexels API.
  - Procedural animated gradient visual renderer with whimsical geometric floating particles (stars, bubbles, sparkles, soft suns) rendered at **1080x1920 (9:16 Shorts)** or **1920x1080 (16:9 Long)**.
- **Harmonic Chime Synthesizer**: Generates gentle, royalty-free background pentatonic chimes mathematically mixed at kid-safe volume levels.
- **Auto-Captions & Subtitle Overlays**: Generates word-wrapped caption badges positioned safely away from YouTube UI elements (Shorts: middle-lower 68% safe zone; Long: bottom 82%).
- **MoviePy & FFmpeg Video Assembly**: Robust multi-track composition with H.264 video and AAC audio encoding.

### 4. YouTube API Integration & Compliance
- **COPPA Compliance**: Enforces `status.selfDeclaredMadeForKids = True` on all uploads, sets kid-appropriate categories (`27 - Education` or `24 - Entertainment`), and checks titles and descriptions against child safety standards.
- **SEO Optimization**: Generates high-CTR, kid-friendly titles, detailed educational descriptions, and relevant hashtag metadata.
- **Dual Mode Operation**: Authenticated OAuth2 uploads via Google API client or automated dry-run mock mode for local testing without YouTube credentials.

---

## Daily Schedule & Quota Matrix

The pipeline targets five Shorts and two long-form videos each day. These local release times use `America/New_York`; daylight-saving changes are handled by the configured timezone, so the corresponding UTC time varies seasonally.

| Slot ID | Time (Eastern) | Format | Aspect Ratio | Target Duration | Theme |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `slot_1_morning_short` | 08:00 AM | Shorts | 9:16 (Vertical) | 30–50 sec | Rotating Shorts topic |
| `slot_2_morning_long` | 10:00 AM | Long | 16:9 (Horizontal) | 3–6 min | Rotating Long topic |
| `slot_3_lunch_short` | 12:00 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Rotating Shorts topic |
| `slot_4_afternoon_short` | 02:30 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Rotating Shorts topic |
| `slot_5_afterschool_long` | 04:30 PM | Long | 16:9 (Horizontal) | 3–6 min | Rotating Long topic |
| `slot_6_dinner_short` | 06:30 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Rotating Shorts topic |
| `slot_7_bedtime_short` | 08:30 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Rotating Shorts topic |

---

## Project Structure

```
.
├── .env.example                     # Environment variables template
├── Dockerfile                       # Production container definition
├── docker-compose.yml               # Celery, Redis, & standalone orchestration
├── pyproject.toml                   # Project packaging and metadata
├── requirements.txt                 # Pinned dependencies
├── src/
│   ├── __init__.py
│   ├── config.py                    # Typed Pydantic configuration & constants
│   ├── logger.py                    # Colored and file-backed structured logging
│   ├── pipeline.py                  # Orchestrator connecting all generation stages
│   ├── cli.py                       # Command-line interface
│   ├── content/                     # Content Generation Engine
│   │   ├── __init__.py
│   │   ├── topics.py                # Topic catalog & educational metadata
│   │   ├── topic_rotator.py         # Daily rotation manager across 7 slots
│   │   ├── prompts.py               # Safe COPPA prompt engineering
│   │   └── script_generator.py      # LLM & procedural script writer
│   ├── production/                  # Media Production Engine
│   │   ├── __init__.py
│   │   ├── voice.py                 # ElevenLabs & gTTS audio voiceover
│   │   ├── visuals.py               # Stock media fetcher & animated canvas
│   │   ├── audio.py                 # Harmonic background chime generator
│   │   ├── subtitles.py             # Safe-zone auto-caption overlay renderer
│   │   └── video_editor.py          # MoviePy & FFmpeg video compositor
│   ├── youtube/                     # Publishing & Compliance
│   │   ├── __init__.py
│   │   ├── compliance.py            # COPPA validator & metadata rules
│   │   ├── seo.py                   # SEO title, tag, and description generator
│   │   ├── client.py                # YouTube API client & dry-run mock
│   │   └── uploader.py              # Resumable video publisher
│   ├── database/                    # Persistence & State Management
│   │   ├── __init__.py
│   │   ├── models.py                # Pydantic data models (VideoJob, Quota)
│   │   └── state_manager.py         # SQLite job status and retry ledger
│   └── scheduler/                   # Scheduling & Queue Management
│       ├── __init__.py
│       ├── daily_schedule.py        # 7-slot daily schedule definition
│       ├── queue_manager.py         # Job executor with automatic retry logic
│       ├── cron_runner.py           # Standalone APScheduler runner
│       └── celery_app.py            # Distributed Celery worker & Beat schedule
└── tests/                           # Unit and integration test suite
    ├── test_config.py
    ├── test_database.py
    ├── test_scheduler_and_pipeline.py
    ├── test_topics_and_scripts.py
    ├── test_voice_and_visuals.py
    └── test_youtube_compliance.py
```

---

## Prerequisites & Installation

### System Dependencies
- **Python**: 3.10, 3.11, or 3.12
- **FFmpeg**: Required for audio/video decoding and encoding.
  ```bash
  # Debian / Ubuntu
  sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu-core

  # macOS (Homebrew)
  brew install ffmpeg

  # Windows (Chocolatey)
  choco install ffmpeg
  ```

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/nirajmallik143-hub/USA-auto.git
   cd USA-auto
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Android / Pydroid 3

Pydroid can run individual jobs, but Android may stop background apps, so the continuous scheduler and daily unattended publishing are not supported on the phone. Video rendering also needs an executable FFmpeg binary; installing the Python `moviepy` package alone does not provide a usable Android FFmpeg binary.

1. Install the Pydroid repository plugin, then put the repository in a folder Pydroid can access and set that folder as its working directory.
2. In Pydroid's terminal, install the phone runtime dependencies:
   ```bash
   pip install -r requirements-android.txt
   ```
   If Pillow or NumPy cannot be installed with pip, install them using Pydroid's repository plugin.
3. Provide an FFmpeg executable that can run from Pydroid's app environment, and set `FFMPEG_BINARY` to its full path before starting Python. Android may prevent executing binaries from shared storage; the binary must be executable from the app.
4. Start with a single preview job (YouTube dry-run is enabled by default):
   ```bash
   python -m src.cli generate-one --format shorts --topic animal_riddles --preview
   ```
   Generated files are saved under the repository's `output/` directory. For a real upload, configure YouTube OAuth credentials and explicitly disable dry-run; the phone must remain awake and connected while rendering and uploading.

The Android dependency profile omits Celery and Redis, which are only needed for distributed cloud workers. If package installation or FFmpeg execution is blocked by the device or Pydroid, run the pipeline on a desktop or cloud host instead.

---

## Environment Configuration

Copy `.env.example` to `.env` and configure your API keys:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `openai`, `anthropic`, or `procedural` | `openai` |
| `OPENAI_API_KEY` | OpenAI API Key | `""` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | `""` |
| `TTS_PROVIDER` | `elevenlabs` or `gtts` | `gtts` |
| `ELEVENLABS_API_KEY`| ElevenLabs API Key | `""` |
| `PEXELS_API_KEY` | Pexels Stock Video API Key | `""` |
| `YOUTUBE_CLIENT_SECRETS_FILE` | Path to `client_secrets.json` | `client_secrets.json` |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///output/pipeline.db` |
| `REDIS_URL` | Redis URL for Celery | `redis://localhost:6379/0` |
| `DRY_RUN_UPLOAD` | Alias of `YOUTUBE_DRY_RUN`; set `false` to really upload | `true` locally (workflow sets `false`) |
| `COPPA_MADE_FOR_KIDS`| Strict "Made for Kids" enforcement | `true` |

> **Offline Mode**: If `OPENAI_API_KEY` or `ELEVENLABS_API_KEY` are left blank, the pipeline gracefully falls back to the internal procedural script engine and `gTTS` voice generation, requiring zero paid external services for full end-to-end operation!

---

## CLI Usage Guide

The pipeline includes a rich CLI for direct operations, testing, and monitoring:

### 1. Check System Health & Quota Status
```bash
# Verify all components, FFmpeg, directories, and credentials
python -m src.cli health

# Check today's quota status and recent jobs
python -m src.cli status
```

### 2. Generate an Ad-Hoc Video
```bash
# Generate a vertical Short (9:16) with animal riddles (preview mode: generates fast 5s preview)
python -m src.cli run-single --format shorts --topic animal_riddles --preview

# Generate a horizontal Long video (16:9) with space facts
python -m src.cli run-single --format long --topic space_facts --preview
```

### 3. Run Today's Full Daily Batch
```bash
# Executes all 7 daily video slots sequentially
python -m src.cli run-daily --preview
```

### 4. Retry Failed Jobs
```bash
# Scans SQLite database for failed jobs and re-runs them
python -m src.cli retry
```

---

## Running the Scheduler

### Production scheduler: Standalone APScheduler
Use one continuously running APScheduler instance for production. It reads slot names and release times from the shared daily schedule, starts production 60 minutes before each release, and uses `America/New_York` to follow daylight-saving time. Keep its SQLite database on persistent storage so job state and daily quotas survive restarts:
```bash
python -m src.scheduler.cron_runner
```

For Docker, start only the standalone scheduler:
```bash
docker compose --profile standalone up -d standalone_scheduler
docker compose logs -f standalone_scheduler
```
The Compose `app_data` volume persists its SQLite state across container restarts.

Do not enable the GitHub Actions scheduled workflow or start Celery Beat at the same time as this production scheduler. Celery remains an optional alternative for a separate deployment; do not run both schedulers against the same channel.

### Optional alternative: Celery + Redis
Only use this instead of APScheduler when intentionally deploying the distributed worker setup:
   ```bash
   docker compose --profile celery up -d
   ```

---

## GitHub Actions (Manual Validation)

The workflow `.github/workflows/main.yml` is manual-only and is not the production scheduler. Use it for controlled validation; its `dry_run` input defaults to true. Do not dispatch a real-upload batch while the production scheduler is running.

### One-time setup checklist

1. **Google Cloud project**: create one at <https://console.cloud.google.com/>.
2. **Enable the API**: APIs & Services > Library > *YouTube Data API v3* > Enable.
3. **OAuth consent screen**: configure it, add yourself as a user, then click **Publish app** so the status is **In production**. If it stays in *Testing*, Google expires the refresh token after **7 days** and uploads silently stop (`invalid_grant`).
4. **OAuth client**: Credentials > Create credentials > OAuth client ID > *Desktop app*. Download the JSON and save it locally as `secrets/client_secrets.json` (it is git-ignored).
5. **Generate the token locally** (a browser window opens; sign in with the YouTube channel owner account):
   ```bash
   python -m src.cli auth            # add --no-browser on a headless machine
   ```
   This writes `secrets/youtube_credentials.json`, which contains a refresh token.
6. **Rotate exposed credentials before enabling uploads.** Previously embedded credentials were committed in workflow history. Revoke and replace them with their providers, then arrange to remove the exposed values from repository history. Removing them from the current workflow does not make the old credentials safe.
7. **Add new values as GitHub secrets** (Settings > Secrets and variables > Actions); never put credential values in workflow YAML:

   | Secret | Value |
   | :--- | :--- |
   | `YOUTUBE_CLIENT_SECRETS_JSON` | full contents of `secrets/client_secrets.json` |
   | `YOUTUBE_TOKEN_JSON` | full contents of `secrets/youtube_credentials.json` |
   | `OPENAI_API_KEY`, `PIXABAY_API_KEY` | optional content and stock-media services |
   | `PEXELS_API_KEY` | optional stock visuals |
   | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | optional failure notifications |

   Repository **variables**: `LLM_PROVIDER` (optional: `procedural` (default), `openai`, `anthropic`). Production credentials must be injected through the deployment platform's secret store, not committed or copied into this repository.
8. **Verify before rollout**: run `python -m src.cli doctor`, then use the manual workflow with dry-run enabled. Once credential rotation, OAuth/channel access, API quota, and test uploads are confirmed, test one Short and one long video with publishing enabled before starting the production scheduler.

### How it stays reliable

- **State**: the production SQLite database must be on persistent storage; the Docker deployment persists it in `app_data`. Manual GitHub Actions runs cache state separately and are not the production ledger.
- **Failures are visible**: `run-daily` / `status --check` exit non-zero when any job FAILED or nothing was uploaded; a GitHub issue (label `automation-failure`) is opened or commented on, and Telegram is notified if configured.
- **Daily success**: inspect `python -m src.cli status` and confirm the persisted quota is 5/5 Shorts and 2/2 long videos. Failed jobs are reported and retried according to the configured retry policy.
- **Quota**: monitor YouTube API usage and upload limits before rollout. If quota prevents seven uploads per day, request the required quota increase; do not treat a scheduled job as a successful upload until state records it completed.

---

## COPPA & Child Safety Compliance

Under the United States Children's Online Privacy Protection Act (COPPA) and YouTube policy:

1. **Mandatory Setting**: Every video uploaded through this pipeline is programmatically submitted with:
   ```json
   "status": {
     "privacyStatus": "public",
     "selfDeclaredMadeForKids": true
   }
   ```
2. **Content Verification**: The script generator prompts enforce positive, gentle, age-appropriate language (preschool through early elementary).
3. **Safety Filters**: Scripts and metadata are validated against forbidden terms (violence, fear, weapons, adult themes) before rendering begins.

---

## Testing & Quality Assurance

The test suite covers configuration, SQLite state management, retry logic, topic rotation, prompt generation, audio/visual synthesis, YouTube COPPA compliance, and scheduler execution:

```bash
# Run complete test suite
pytest -v

# Run with coverage report
pytest --cov=src tests/
```

All 24 unit and integration tests execute with zero external API requirements using mocks and the procedural engine.
