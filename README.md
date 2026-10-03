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
- [Android: Create YouTube OAuth Tokens with Replit](#android-create-youtube-oauth-tokens-with-replit)
- [Environment Configuration](#environment-configuration)
- [CLI Usage Guide](#cli-usage-guide)
- [Running the Scheduler](#running-the-scheduler)
  - [Option 1: Standalone APScheduler (Local / VM)](#option-1-standalone-apscheduler-local--vm)
  - [Option 2: Celery + Redis (Distributed Cloud)](#option-2-celery--redis-distributed-cloud)
  - [Option 3: Docker & Docker Compose](#option-3-docker--docker-compose)
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

The pipeline distributes 7 video releases throughout the day (US Eastern Time):

| Slot ID | Time (EST) | Time (UTC) | Format | Aspect Ratio | Target Duration | Theme Affinity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `slot_1_morning_short` | 07:00 AM | 11:00 AM | Shorts | 9:16 (Vertical) | 30–50 sec | Alphabet / Numbers |
| `slot_2_morning_long` | 09:30 AM | 01:30 PM | Long | 16:9 (Horizontal) | 3–6 min | Moral Stories / Space Facts |
| `slot_3_midday_short` | 12:00 PM | 04:00 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Animal Riddles |
| `slot_4_afternoon_short` | 02:30 PM | 06:30 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Kids Jokes & Puzzles |
| `slot_5_afternoon_long` | 04:30 PM | 08:30 PM | Long | 16:9 (Horizontal) | 3–6 min | Science / Dinosaurs |
| `slot_6_early_evening_short` | 06:30 PM | 10:30 PM | Shorts | 9:16 (Vertical) | 30–50 sec | Dinosaur Fun Facts |
| `slot_7_bedtime_short` | 08:00 PM | 12:00 AM | Shorts | 9:16 (Vertical) | 30–50 sec | Bedtime Wonder / Calm Riddle |

---

## Android: Create YouTube OAuth Tokens with Replit

If you only have an Android phone and cannot run Python on it, follow the [Replit YouTube OAuth guide](docs/android-replit-youtube-oauth.md). It explains how to create the tokens and add them to GitHub Actions without putting credentials in this repository.

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
| `DRY_RUN_UPLOAD` | Set `true` to test uploads without posting | `false` |
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

### Option 1: Standalone APScheduler (Local / VM)
Runs continuously as a background Python service using APScheduler:
```bash
python -m src.scheduler.cron_runner
```
- Schedules jobs at the 7 configured daily release times.
- Runs a failed-job retry pass every 30 minutes.
- Resets daily quota tracker at midnight.

### Option 2: Celery + Redis (Distributed Cloud)
For distributed setups running on AWS, GCP, or a dedicated VPS:

1. **Start Redis**:
   ```bash
   redis-server
   ```

2. **Start Celery Worker**:
   ```bash
   celery -A src.scheduler.celery_app worker --loglevel=info --concurrency=2
   ```

3. **Start Celery Beat Scheduler**:
   ```bash
   celery -A src.scheduler.celery_app beat --loglevel=info
   ```

### Option 3: Docker & Docker Compose
The easiest way to run the complete distributed stack:

```bash
# Build and start Redis, Celery Worker, and Celery Beat
docker-compose up -d

# Check service logs
docker-compose logs -f celery_worker

# To run the standalone APScheduler container instead:
docker-compose --profile standalone up -d standalone_scheduler
```

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
