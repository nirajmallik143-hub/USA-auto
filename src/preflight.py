"""
Preflight ("doctor") checks that verify the environment can produce and upload videos.
"""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.config import LLMProvider, TTSEngine, settings


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    warning: bool = False  # a failed optional check: reported but does not fail the run


def check_ffmpeg() -> CheckResult:
    path = shutil.which("ffmpeg")
    if path:
        return CheckResult("ffmpeg", True, f"found at {path}")
    return CheckResult("ffmpeg", False, "ffmpeg is not installed (apt-get install ffmpeg)")


def check_env() -> List[CheckResult]:
    results: List[CheckResult] = []
    if not settings.youtube_dry_run:
        for label, path in (
            ("YouTube client secrets", settings.youtube_client_secrets_file),
            ("YouTube token", settings.youtube_credentials_file),
        ):
            exists = Path(path).exists()
            results.append(CheckResult(
                f"credentials: {label}", exists,
                f"{path} present" if exists else f"{path} missing (set YOUTUBE_CLIENT_SECRETS_JSON / YOUTUBE_TOKEN_JSON secrets)",
            ))
    if settings.llm_provider == LLMProvider.OPENAI and not settings.openai_api_key:
        results.append(CheckResult("env: OPENAI_API_KEY", False, "not set; falling back to procedural scripts", warning=True))
    if settings.llm_provider == LLMProvider.ANTHROPIC and not settings.anthropic_api_key:
        results.append(CheckResult("env: ANTHROPIC_API_KEY", False, "not set; falling back to procedural scripts", warning=True))
    if settings.tts_engine == TTSEngine.ELEVENLABS and not settings.elevenlabs_api_key:
        results.append(CheckResult("env: ELEVENLABS_API_KEY", False, "not set; falling back to gTTS", warning=True))
    if not settings.pexels_api_key:
        results.append(CheckResult("env: PEXELS_API_KEY", False, "not set; using procedural visuals", warning=True))
    if not results:
        results.append(CheckResult("env", True, "all required variables present"))
    return results


def check_youtube() -> List[CheckResult]:
    if settings.youtube_dry_run:
        return [CheckResult("youtube", True, "dry-run enabled: token and channel checks skipped", warning=True)]

    from src.youtube.client import YouTubeAuthError, load_credentials

    try:
        creds = load_credentials()
    except YouTubeAuthError as e:
        return [CheckResult("youtube token", False, str(e))]
    results = [CheckResult("youtube token", True, "valid (refreshed if needed)")]

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        client = build("youtube", "v3", credentials=creds, cache_discovery=False)
        resp = client.channels().list(part="id,snippet", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            results.append(CheckResult("youtube channel", False, "token is valid but no YouTube channel is attached to the account"))
        else:
            results.append(CheckResult("youtube channel", True, f"reachable: {items[0]['snippet']['title']}"))
    except HttpError as e:
        hint = " (token lacks scope; re-run `python -m src.cli auth`)" if e.resp.status == 403 else ""
        results.append(CheckResult("youtube channel", False, f"channels.list failed with HTTP {e.resp.status}{hint}"))
    except Exception as e:
        results.append(CheckResult("youtube channel", False, f"channels.list failed: {e}"))
    return results


def check_writable() -> List[CheckResult]:
    results = []
    for label, directory in (("output dir", settings.output_dir), ("storage dir", settings.storage_dir)):
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=directory):
                pass
            results.append(CheckResult(label, True, f"{directory} is writable"))
        except OSError as e:
            results.append(CheckResult(label, False, f"{directory} is not writable: {e}"))
    return results


def run_doctor() -> List[CheckResult]:
    results = [check_ffmpeg()]
    results += check_env()
    results += check_youtube()
    results += check_writable()
    return results
