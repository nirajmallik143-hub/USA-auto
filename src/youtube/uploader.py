"""
YouTube video uploader with scheduled release slots and COPPA compliance.
Handles resumable video uploads and tracks upload states.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import settings
from src.content.script_generator import ScriptData
from src.logger import logger
from src.youtube.client import get_youtube_client
from src.youtube.compliance import compliance_validator
from src.youtube.seo import seo_optimizer


@dataclass
class UploadResult:
    success: bool
    youtube_id: Optional[str] = None
    youtube_url: Optional[str] = None
    title: Optional[str] = None
    privacy_status: Optional[str] = None
    publish_at: Optional[str] = None
    error_message: Optional[str] = None


class YouTubeUploader:
    """Manages publishing videos to YouTube Data API v3."""

    def __init__(self, client=None):
        self._client = client

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
        privacy_status = settings.youtube_privacy_status
        publish_at_iso: Optional[str] = None

        if scheduled_publish_time:
            try:
                # Validate format or parse
                dt = datetime.fromisoformat(scheduled_publish_time.replace("Z", "+00:00"))
                # If scheduling in the future, privacy MUST be private
                if dt > datetime.now(timezone.utc):
                    privacy_status = "private"
                    publish_at_iso = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            except Exception as e:
                logger.warning(f"Could not parse scheduled_publish_time '{scheduled_publish_time}': {e}")

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
            # Check if live or mock client
            if hasattr(self.client, "insert") or isinstance(self.client, type(get_youtube_client())):
                # Mock client branch
                req = self.client.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=str(video_path),
                )
                response = req.execute()
            else:
                # Live Google API client with MediaFileUpload
                from googleapiclient.http import MediaFileUpload

                media = MediaFileUpload(
                    str(video_path),
                    mimetype="video/mp4",
                    resumable=True,
                    chunksize=5 * 1024 * 1024,
                )
                request = self.client.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=media,
                )
                response = None
                while response is None:
                    _, response = request.next_chunk()

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

        except Exception as e:
            err_msg = f"YouTube API upload error: {str(e)}"
            logger.error(err_msg)
            return UploadResult(success=False, error_message=err_msg)


youtube_uploader = YouTubeUploader()
