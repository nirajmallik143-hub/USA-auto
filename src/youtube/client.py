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


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeAuthError(RuntimeError):
    """Raised when YouTube OAuth credentials are missing, invalid, or revoked."""


def load_credentials(credentials_file: Optional[Path] = None):
    """
    Load OAuth credentials from disk, refresh them when expired, and persist the refreshed token.
    Raises YouTubeAuthError with an actionable message when credentials cannot be used.
    """
    from google.auth.exceptions import RefreshError, TransportError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    path = Path(credentials_file or settings.youtube_credentials_file)
    if not path.exists():
        raise YouTubeAuthError(
            f"YouTube token file not found at '{path}'. Run `python -m src.cli auth` locally to create it "
            "and store its contents in the YOUTUBE_TOKEN_JSON GitHub secret."
        )

    try:
        creds = Credentials.from_authorized_user_file(str(path))
    except (ValueError, KeyError) as e:
        raise YouTubeAuthError(
            f"YouTube token file '{path}' is not a valid authorized-user token ({e}). "
            "Re-run `python -m src.cli auth` and update the YOUTUBE_TOKEN_JSON secret."
        ) from e

    if creds.valid:
        return creds

    if not creds.refresh_token:
        raise YouTubeAuthError(
            "YouTube token has no refresh_token. Re-run `python -m src.cli auth` "
            "(consent must be granted with offline access) and update YOUTUBE_TOKEN_JSON."
        )

    try:
        creds.refresh(Request())
    except RefreshError as e:
        detail = str(e)
        if "invalid_grant" in detail:
            raise YouTubeAuthError(
                "YouTube refresh token was rejected (invalid_grant): it is expired or revoked. "
                "If the OAuth consent screen is in 'Testing' mode, refresh tokens expire after 7 days - "
                "publish the app to 'In production'. Then re-run `python -m src.cli auth` and update the "
                "YOUTUBE_TOKEN_JSON secret."
            ) from e
        raise YouTubeAuthError(f"Failed to refresh YouTube token: {detail}") from e
    except TransportError as e:
        raise YouTubeAuthError(f"Network error while refreshing YouTube token: {e}") from e

    try:
        path.write_text(creds.to_json(), encoding="utf-8")
    except OSError as e:
        logger.warning(f"Could not persist refreshed YouTube token to '{path}': {e}")
    return creds


def get_youtube_client():
    """
    Returns an authenticated YouTube API client, or a Mock client in dry-run mode.
    In live mode, authentication problems raise YouTubeAuthError instead of silently mocking.
    """
    if settings.youtube_dry_run:
        logger.info("Using MockYouTubeClient (YOUTUBE_DRY_RUN enabled)")
        return MockYouTubeClient()

    from googleapiclient.discovery import build

    creds = load_credentials()
    client = build("youtube", "v3", credentials=creds, cache_discovery=False)
    logger.info("Authenticated live YouTube Data API v3 client")
    return client


def run_auth_flow(client_secrets_file: Optional[Path] = None, output_file: Optional[Path] = None, open_browser: bool = True) -> Path:
    """
    Interactive OAuth consent flow (run locally). Saves an authorized-user token that contains a
    refresh token, suitable for the YOUTUBE_TOKEN_JSON secret.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets_path = Path(client_secrets_file or settings.youtube_client_secrets_file)
    if not secrets_path.exists():
        raise YouTubeAuthError(
            f"OAuth client secrets file not found at '{secrets_path}'. Download it from Google Cloud Console "
            "(APIs & Services > Credentials > OAuth client ID of type 'Desktop app')."
        )
    out_path = Path(output_file or settings.youtube_credentials_file)

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    creds = flow.run_local_server(
        port=0, open_browser=open_browser, access_type="offline", prompt="consent"
    )
    if not creds.refresh_token:
        raise YouTubeAuthError(
            "Google did not return a refresh token. Revoke the app at https://myaccount.google.com/permissions "
            "and run the auth command again."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(creds.to_json(), encoding="utf-8")
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    return out_path
