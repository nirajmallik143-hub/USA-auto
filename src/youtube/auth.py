"""
One-time YouTube OAuth setup and credential health checks.

`authorize()` runs the Google consent flow on your computer and returns a token JSON
containing a long-lived refresh_token. Store that JSON as the YOUTUBE_TOKEN_JSON secret
so unattended runs (GitHub Actions, servers) can upload without a browser.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import settings
from src.logger import logger
from src.youtube.client import YOUTUBE_SCOPES, YouTubeAuthError, load_live_credentials


def _client_config(client_secrets_file: Optional[Path]) -> Dict[str, Any]:
    if settings.youtube_client_secrets_json and settings.youtube_client_secrets_json.strip():
        return json.loads(settings.youtube_client_secrets_json)

    path = client_secrets_file or settings.youtube_client_secrets_file
    if not path.exists():
        raise YouTubeAuthError(
            f"OAuth client secrets not found at {path}. Download the 'Desktop app' OAuth client JSON "
            "from Google Cloud Console > APIs & Services > Credentials and pass it with --client-secrets."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def authorize(client_secrets_file: Optional[Path] = None, open_browser: bool = True) -> str:
    """Run the interactive OAuth flow and return the authorized-user token JSON."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(_client_config(client_secrets_file), scopes=YOUTUBE_SCOPES)
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=open_browser,
        authorization_prompt_message="\nOpen this URL in your browser to authorize YouTube uploads:\n{url}\n",
    )

    if not creds.refresh_token:
        raise YouTubeAuthError("Google did not return a refresh_token. Revoke the app's access and try again.")

    token_json = creds.to_json()
    settings.youtube_credentials_file.parent.mkdir(parents=True, exist_ok=True)
    settings.youtube_credentials_file.write_text(token_json, encoding="utf-8")
    logger.info(f"Saved YouTube token to {settings.youtube_credentials_file}")
    return token_json


def verify_channel() -> Dict[str, Any]:
    """Confirm the credentials work and return the authenticated channel's basic info."""
    from googleapiclient.discovery import build

    creds = load_live_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    response = youtube.channels().list(part="snippet,status", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise YouTubeAuthError("Authenticated Google account has no YouTube channel.")

    channel = items[0]
    return {
        "id": channel["id"],
        "title": channel["snippet"]["title"],
        "made_for_kids_default": channel.get("status", {}).get("madeForKids"),
    }
