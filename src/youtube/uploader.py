"""
YouTube video uploader with scheduled release slots and COPPA compliance.
Handles resumable video uploads and tracks upload states.
"""

import json
import random
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httplib2
from googleapiclient.errors import HttpError

from src.config import settings
from src.content.script_generator import ScriptData
from src.logger import logger
from src.youtube.client import MockYouTubeClient, YouTubeAuthError, get_youtube_client
from src.youtube.compliance import compliance_validator
from src.youtube.seo import seo_optimizer


MAX_TITLE_CHARS = 100
MAX_DESCRIPTION_BYTES = 5000
MAX_TAGS_CHARS = 500
MAX_UPLOAD_RETRIES = 8
MAX_BACKOFF_SECONDS = 64
RETRIABLE_STATUS_CODES = {500, 502, 503, 504}
HALT_ERROR_CODES = {"quotaExceeded", "uploadLimitExceeded", "dailyLimitExceeded", "auth"}
NETWORK_ERRORS = (ConnectionError, TimeoutError, socket.gaierror, httplib2.HttpLib2Error)


def validate_title(title: str) -> str:
    """YouTube titles: non-empty, <= 100 characters, no angle brackets."""
    clean = " ".join(title.replace("<", "").replace(">", "").split())
    if len(clean) > MAX_TITLE_CHARS:
        clean = clean[:MAX_TITLE_CHARS].rstrip()
    return clean or "Fun Learning Video for Kids"


def validate_description(description: str) -> str:
    """YouTube descriptions: <= 5000 bytes (UTF-8), no angle brackets."""
    clean = description.replace("<", "").replace(">", "")
    encoded = clean.encode("utf-8")
    if len(encoded) > MAX_DESCRIPTION_BYTES:
        clean = encoded[:MAX_DESCRIPTION_BYTES].decode("utf-8", errors="ignore").rstrip()
    return clean


def validate_tags(tags: List[str]) -> List[str]:
    """YouTube tags: total length <= 500 chars (tags containing spaces count 2 extra for quotes)."""
    result: List[str] = []
    total = 0
    for tag in tags:
        clean = tag.replace("<", "").replace(">", "").replace(",", " ").strip()
        if not clean:
            continue
        cost = len(clean) + (2 if " " in clean else 0) + (1 if result else 0)
        if total + cost > MAX_TAGS_CHARS:
            break
        result.append(clean)
        total += cost
    return result


def resolve_publish_at(scheduled_publish_time: Optional[str]) -> Optional[str]:
    """Return a future RFC 3339 UTC timestamp (…Z) or None if absent/invalid/not in the future."""
    if not scheduled_publish_time:
        return None
    try:
        dt = datetime.fromisoformat(scheduled_publish_time.replace("Z", "+00:00"))
    except ValueError as e:
        logger.warning(f"Could not parse scheduled_publish_time '{scheduled_publish_time}': {e}")
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    if dt <= datetime.now(timezone.utc):
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_http_error(error: HttpError) -> Tuple[Optional[str], str]:
    """Extract (reason, raw body) from a googleapiclient HttpError."""
    raw = error.content.decode("utf-8", errors="replace") if isinstance(error.content, bytes) else str(error.content)
    reason: Optional[str] = None
    try:
        errors = json.loads(raw).get("error", {}).get("errors", [])
        if errors:
            reason = errors[0].get("reason")
    except (ValueError, AttributeError):
        pass
    return reason, raw


@dataclass
class UploadResult:
    success: bool
    youtube_id: Optional[str] = None
    youtube_url: Optional[str] = None
    title: Optional[str] = None
    privacy_status: Optional[str] = None
    publish_at: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None  # e.g. quotaExceeded, uploadLimitExceeded, auth

    @property
    def should_halt(self) -> bool:
        """True when further uploads in this run would fail for the same reason."""
        return self.error_code in HALT_ERROR_CODES


class YouTubeUploader:
    """Manages publishing videos to YouTube Data API v3."""

    def __init__(self, client=None, sleep=time.sleep):
        self._client = client
        self._sleep = sleep

    @property
    def client(self):
        if self._client is None:
            self._client = get_youtube_client()
        return self._client

    def upload_video(
        self,
        video_path: Path,
        script: ScriptData,
        scheduled_publish_time: Optional[str] = None,
    ) -> UploadResult:
        """
        Uploads and schedules a video on YouTube:
        1. Validates COPPA kids compliance.
        2. Applies SEO optimizations (title, description, tags).
        3. Configures pre-scheduled publishing slot if specified.
        4. Transmits upload via YouTube Data API v3.
        """
        if not video_path.exists():
            return UploadResult(
                success=False,
                error_message=f"Video file not found at: {video_path}",
            )

        # 1. SEO Optimizations
        opt_title = seo_optimizer.optimize_title(script.title, script.video_format, script.topic)
        opt_desc = seo_optimizer.optimize_description(script.description, script)
        opt_tags = seo_optimizer.optimize_tags(script.tags, script.topic)
        opt_title = validate_title(opt_title)
        opt_desc = validate_description(opt_desc)
        opt_tags = validate_tags(opt_tags)

        # 2. Compliance Check
        compliance = compliance_validator.validate_metadata(
            title=opt_title,
            description=opt_desc,
            tags=opt_tags,
            topic=script.topic,
        )

        if not compliance.is_compliant:
            logger.error(f"Cannot upload non-compliant video: {compliance.reasons}")
            return UploadResult(
                success=False,
                error_message=f"Compliance check failed: {'; '.join(compliance.reasons)}",
            )

        # 3. Scheduling & Privacy Configuration
        publish_at_iso = resolve_publish_at(scheduled_publish_time)
        if publish_at_iso:
            # publishAt requires privacyStatus=private
            privacy_status = "private"
        else:
            privacy_status = settings.youtube_privacy_status
            if privacy_status not in ("public", "private", "unlisted"):
                # "scheduled" is not a valid API value; publish immediately when there is no future slot
                privacy_status = "public"

        # 4. Construct YouTube API Request Body
        body = {
            "snippet": {
                "title": opt_title,
                "description": opt_desc,
                "tags": opt_tags,
                "categoryId": compliance.category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en-US",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": True,  # COPPA mandate
                "embeddable": True,
            },
        }

        if publish_at_iso:
            body["status"]["publishAt"] = publish_at_iso

        logger.info(
            f"Preparing YouTube upload: '{opt_title}' "
            f"[Format: {script.video_format}, Category: {compliance.category_id}, Privacy: {privacy_status}]"
        )

        # 5. Execute Upload
        try:
            client = self.client
            if isinstance(client, MockYouTubeClient):
                media = str(video_path)
            else:
                from googleapiclient.http import MediaFileUpload

                media = MediaFileUpload(
                    str(video_path),
                    mimetype="video/mp4",
                    resumable=True,
                    chunksize=5 * 1024 * 1024,
                )
            request = client.videos().insert(part="snippet,status", body=body, media_body=media)
            response = self._resumable_upload(request)

            yt_id = response.get("id")
            yt_url = f"https://www.youtube.com/watch?v={yt_id}"

            logger.info(f"Successfully published video to YouTube! ID={yt_id}, URL={yt_url}")
            return UploadResult(
                success=True,
                youtube_id=yt_id,
                youtube_url=yt_url,
                title=opt_title,
                privacy_status=privacy_status,
                publish_at=publish_at_iso,
            )

        except YouTubeAuthError as e:
            logger.error(f"YouTube authentication failed: {e}")
            return UploadResult(success=False, error_message=f"YouTube auth error: {e}", error_code="auth")
        except HttpError as e:
            reason, raw = parse_http_error(e)
            logger.error(f"YouTube API error (HTTP {e.resp.status}, reason={reason}): {raw}")
            code = reason
            if e.resp.status == 401:
                code = "auth"
            return UploadResult(
                success=False,
                error_message=f"YouTube API upload error (HTTP {e.resp.status}, {reason}): {raw[:500]}",
                error_code=code,
            )
        except Exception as e:
            err_msg = f"YouTube API upload error: {str(e)}"
            logger.error(err_msg)
            return UploadResult(success=False, error_message=err_msg)

    def _resumable_upload(self, request) -> Dict[str, Any]:
        """Drive a resumable upload, retrying 5xx/network errors with exponential backoff."""
        response = None
        retries = 0
        total_retries = 0
        while response is None:
            try:
                status, response = request.next_chunk()
                if status is not None:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")
                retries = 0
            except HttpError as e:
                if e.resp.status not in RETRIABLE_STATUS_CODES:
                    raise
                self._backoff(retries, f"HTTP {e.resp.status}", total_retries)
                retries += 1
                total_retries += 1
            except NETWORK_ERRORS as e:
                self._backoff(retries, type(e).__name__, total_retries)
                retries += 1
                total_retries += 1
        return response

    def _backoff(self, attempt: int, reason: str, total: int = 0) -> None:
        if attempt >= MAX_UPLOAD_RETRIES or total >= MAX_UPLOAD_RETRIES * 4:
            raise RuntimeError(f"Upload failed after {MAX_UPLOAD_RETRIES} retries (last error: {reason})")
        delay = min(2 ** attempt + random.random(), MAX_BACKOFF_SECONDS)
        logger.warning(f"Retriable upload error ({reason}); retry {attempt + 1}/{MAX_UPLOAD_RETRIES} in {delay:.1f}s")
        self._sleep(delay)


youtube_uploader = YouTubeUploader()
