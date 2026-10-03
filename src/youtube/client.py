"""
YouTube Data API v3 client factory.
Provides live Google API client or a fully functional Mock client for dry-run/testing.
"""

import datetime
import uuid
from typing import Any, Dict, Optional
from pathlib import Path

from src.config import settings
from src.logger import logger

YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


class MockYouTubeRequest:
    """Simulates an executable YouTube API request."""

    def __init__(self, body: Dict[str, Any], media_body: Any):
        self.body = body
        self.media_body = media_body

    def execute(self) -> Dict[str, Any]:
        """Validate request payload and return simulated YouTube response."""
        snippet = self.body.get("snippet", {})
        status = self.body.get("status", {})

        # Validation check for Made for Kids compliance
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


def get_youtube_client():
    """
    Returns a live authenticated YouTube API client or the dry-run mock.
    """
    if settings.youtube_dry_run:
        logger.info("Using MockYouTubeClient (dry run mode)")
        return MockYouTubeClient()

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not settings.youtube_credentials_file.exists():
            raise RuntimeError(
                "YouTube OAuth credentials are not configured. Run "
                "'python -m src.cli youtube-auth' to authorize this account."
            )

        creds = Credentials.from_authorized_user_file(
            str(settings.youtube_credentials_file),
            scopes=YOUTUBE_UPLOAD_SCOPE,
        )
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
            _save_credentials(creds)
        if not creds.valid:
            raise RuntimeError(
                "YouTube OAuth credentials are invalid or expired. Run "
                "'python -m src.cli youtube-auth' to authorize this account again."
            )

        client = build("youtube", "v3", credentials=creds)
        logger.info("Authenticated live YouTube Data API v3 client")
        return client
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to initialize live YouTube client: {e}") from e


def _save_credentials(credentials) -> None:
    """Persist OAuth tokens with owner-only file permissions where supported."""
    token_path = settings.youtube_credentials_file
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    token_path.chmod(0o600)


def authenticate_youtube():
    """Run the interactive first-time OAuth flow and persist the refresh token."""
    if not settings.youtube_client_secrets_file.exists():
        raise RuntimeError(
            "YouTube OAuth client secrets were not found at "
            f"{settings.youtube_client_secrets_file}."
        )

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(
            str(settings.youtube_client_secrets_file),
            YOUTUBE_UPLOAD_SCOPE,
        )
        credentials = flow.run_local_server(port=0)
        _save_credentials(credentials)
        logger.info(f"Saved YouTube OAuth credentials to {settings.youtube_credentials_file}")
        return credentials
    except Exception as e:
        raise RuntimeError(f"YouTube OAuth authorization failed: {e}") from e
