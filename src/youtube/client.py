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


def get_youtube_client():
    """
    Returns an authenticated YouTube API client or Mock client if dry run / offline.
    """
    if settings.youtube_dry_run or not settings.youtube_credentials_file.exists():
        logger.info("Using MockYouTubeClient (dry run mode or no credentials configured)")
        return MockYouTubeClient()

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(settings.youtube_credentials_file))
        client = build("youtube", "v3", credentials=creds)
        logger.info("Authenticated live YouTube Data API v3 client")
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize live YouTube client ({e}), falling back to MockYouTubeClient")
        return MockYouTubeClient()
