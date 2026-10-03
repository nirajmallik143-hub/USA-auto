"""
YouTube Data API v3 client factory.
Provides live Google API client or a fully functional Mock client for dry-run/testing.
"""

import json
import uuid
from typing import Any, Dict, Optional

from src.config import settings
from src.logger import logger

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeAuthError(RuntimeError):
    """Raised when live uploads are requested but credentials are missing or invalid."""


class MockYouTubeRequest:
    """Simulates an executable YouTube API request."""

    def __init__(self, body: Dict[str, Any], media_body: Any):
        self.body = body
        self.media_body = media_body

    def execute(self) -> Dict[str, Any]:
        """Validate request payload and return simulated YouTube response."""
        snippet = self.body.get("snippet", {})
        status = self.body.get("status", {})

        if not status.get("selfDeclaredMadeForKids"):
            raise ValueError("YouTube API Error: 'selfDeclaredMadeForKids' must be True for kids content!")

        mock_id = f"yt_mock_{uuid.uuid4().hex[:11]}"
        logger.info(f"[DRY-RUN] Simulated YouTube upload successful: ID={mock_id}, Title='{snippet.get('title')}'")

        return {
            "id": mock_id,
            "kind": "youtube#video",
            "snippet": snippet,
            "status": {
                "uploadStatus": "uploaded",
                "privacyStatus": status.get("privacyStatus", "public"),
                "publishAt": status.get("publishAt"),
                "selfDeclaredMadeForKids": True,
            },
        }

    def next_chunk(self):
        """Simulate chunked resumable upload completion."""
        return None, self.execute()


class MockYouTubeVideosResource:
    """Simulates the youtube.videos() resource."""

    def insert(self, part: str, body: Dict[str, Any], media_body: Any = None) -> MockYouTubeRequest:
        return MockYouTubeRequest(body=body, media_body=media_body)


class MockYouTubeClient:
    """Mock YouTube client that allows offline testing and dry runs."""

    def videos(self) -> MockYouTubeVideosResource:
        return MockYouTubeVideosResource()


def _load_token_info() -> Optional[Dict[str, Any]]:
    """Load the authorized-user token from the env var or the credentials file."""
    if settings.youtube_token_json and settings.youtube_token_json.strip():
        return json.loads(settings.youtube_token_json)
    if settings.youtube_credentials_file.exists():
        return json.loads(settings.youtube_credentials_file.read_text(encoding="utf-8"))
    return None


def load_live_credentials():
    """
    Build refreshed Google OAuth credentials for the YouTube Data API.
    Raises YouTubeAuthError with an actionable message when something is wrong.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    try:
        token_info = _load_token_info()
    except json.JSONDecodeError as e:
        raise YouTubeAuthError(f"YouTube token JSON is not valid JSON: {e}") from e

    if not token_info:
        raise YouTubeAuthError(
            "No YouTube credentials found. Run `python -m src.cli youtube-auth` once on your computer, "
            "then store the printed JSON as the YOUTUBE_TOKEN_JSON secret "
            f"(or save it to {settings.youtube_credentials_file})."
        )

    if not token_info.get("refresh_token"):
        raise YouTubeAuthError(
            "YouTube token has no refresh_token, so it cannot be renewed automatically. "
            "Re-run `python -m src.cli youtube-auth` to generate a new token."
        )

    creds = Credentials.from_authorized_user_info(token_info, scopes=YOUTUBE_SCOPES)

    if not creds.valid:
        try:
            creds.refresh(Request())
            logger.info("Refreshed YouTube OAuth access token")
        except Exception as e:
            raise YouTubeAuthError(
                f"Could not refresh YouTube token ({e}). If your Google OAuth consent screen is in "
                "'Testing' mode, refresh tokens expire after 7 days — publish the app to 'In production' "
                "and re-run `python -m src.cli youtube-auth`."
            ) from e

    try:
        settings.youtube_credentials_file.parent.mkdir(parents=True, exist_ok=True)
        settings.youtube_credentials_file.write_text(creds.to_json(), encoding="utf-8")
    except OSError as e:
        logger.warning(f"Could not persist refreshed YouTube token: {e}")

    return creds


def get_youtube_client():
    """
    Returns an authenticated YouTube API client, or a Mock client in dry-run mode.
    When dry-run is disabled, credential problems raise instead of silently faking uploads.
    """
    if settings.youtube_dry_run:
        logger.info("Using MockYouTubeClient (YOUTUBE_DRY_RUN=true)")
        return MockYouTubeClient()

    from googleapiclient.discovery import build

    creds = load_live_credentials()
    client = build("youtube", "v3", credentials=creds, cache_discovery=False)
    logger.info("Authenticated live YouTube Data API v3 client")
    return client
