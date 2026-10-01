"""
Unified pipeline coordinator.
Orchestrates Script Generation -> Voiceover -> Visuals -> Video Assembly -> YouTube Upload
with robust error handling, state tracking, and retry coordination.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from src.config import VideoFormat, settings
from src.content.script_generator import ScriptData, script_generator
from src.content.topic_rotator import topic_rotator
from src.database.models import JobStatus, VideoJob
from src.database.state_manager import StateManager, state_manager
from src.logger import logger
from src.production.video_editor import video_editor
from src.youtube.uploader import youtube_uploader


class VideoProductionPipeline:
    """End-to-end coordinator for the automated video pipeline."""

    def __init__(self, db: Optional[StateManager] = None):
        self.db = db or state_manager

    def run_job(
        self,
        video_format: str,
        topic: Optional[str] = None,
        slot_name: str = "manual_ad_hoc",
        scheduled_time: Optional[str] = None,
        job_id: Optional[str] = None,
        preview_mode: bool = False,
        enforce_quota: bool = True,
    ) -> VideoJob:
        """
        Execute full lifecycle for a video job:
        1. Quota check
        2. Create Job in DB
        3. Script Generation
        4. Video Production
        5. YouTube Upload & Schedule
        6. State & Quota Update
        """
        target_date = (scheduled_time or datetime.now(timezone.utc).isoformat())[:10]

        # 1. Quota check
        if enforce_quota and not self.db.can_schedule_more(target_date, video_format):
            logger.warning(
                f"Daily quota for {video_format} on {target_date} is already satisfied! "
                "Skipping to protect daily quota."
            )
            quota = self.db.get_daily_quota(target_date)
            # Create a completed or cancelled marker job if needed
            return self.db.create_job(
                video_format=video_format,
                topic=topic or "quota_reached",
                slot_name=slot_name,
                scheduled_time=scheduled_time,
                job_id=job_id,
            )

        # Determine Topic
        resolved_topic = topic or topic_rotator.select_next_topic(video_format, target_date)

        # 2. Create Job in DB
        job = self.db.create_job(
            video_format=video_format,
            topic=resolved_topic,
            slot_name=slot_name,
            scheduled_time=scheduled_time,
            job_id=job_id,
        )

        try:
            # 3. Script Generation
            self.db.update_job_status(job.id, JobStatus.GENERATING_SCRIPT, increment_attempt=True)
            script = script_generator.generate_script(video_format=video_format, topic=resolved_topic)

            self.db.update_job_status(
                job.id,
                JobStatus.ASSEMBLING_VIDEO,
                script_data=script.to_dict(),
            )

            # 4. Video Assembly
            video_path, duration = video_editor.produce_video(
                script=script,
                job_id=job.id,
                preview_mode=preview_mode,
            )

            self.db.update_job_status(
                job.id,
                JobStatus.UPLOADING,
                video_path=str(video_path),
                duration_seconds=duration,
            )

            # 5. YouTube Upload
            upload_result = youtube_uploader.upload_video(
                video_path=video_path,
                script=script,
                scheduled_publish_time=scheduled_time,
            )

            if not upload_result.success:
                raise RuntimeError(upload_result.error_message or "YouTube upload failed")

            # 6. Complete Job
            completed_job = self.db.update_job_status(
                job.id,
                JobStatus.COMPLETED,
                youtube_id=upload_result.youtube_id,
                youtube_url=upload_result.youtube_url,
            )
            logger.info(f"Video job {job.id} completed successfully! URL: {upload_result.youtube_url}")
            return completed_job

        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(f"Job {job.id} failed: {error_msg}")
            failed_job = self.db.update_job_status(
                job.id,
                JobStatus.FAILED,
                error_message=error_msg,
            )
            return failed_job

    def retry_job(self, job_id: str, preview_mode: bool = False) -> Optional[VideoJob]:
        """
        Retry a previously failed job.
        Maintains the original slot and daily quota tracking.
        """
        job = self.db.get_job(job_id)
        if not job:
            logger.error(f"Cannot retry job {job_id}: not found")
            return None

        if job.status == JobStatus.COMPLETED:
            logger.info(f"Job {job_id} is already completed. Skipping retry.")
            return job

        if job.attempt_count >= job.max_retries:
            logger.warning(f"Job {job_id} has exceeded maximum retries ({job.max_retries}). Cannot retry.")
            return job

        logger.info(f"Retrying job {job_id} (attempt {job.attempt_count + 1}/{job.max_retries})")

        try:
            # Check if script exists, otherwise regenerate
            if job.script_data:
                script = ScriptData.from_dict(job.script_data)
            else:
                self.db.update_job_status(job.id, JobStatus.GENERATING_SCRIPT, increment_attempt=True)
                script = script_generator.generate_script(job.video_format, job.topic)
                self.db.update_job_status(job.id, JobStatus.ASSEMBLING_VIDEO, script_data=script.to_dict())

            # Check if video exists, otherwise re-render
            video_path = Path(job.video_path) if job.video_path else None
            duration = job.duration_seconds

            if not video_path or not video_path.exists():
                self.db.update_job_status(job.id, JobStatus.ASSEMBLING_VIDEO)
                video_path, duration = video_editor.produce_video(
                    script=script,
                    job_id=job.id,
                    preview_mode=preview_mode,
                )
                self.db.update_job_status(
                    job.id,
                    JobStatus.UPLOADING,
                    video_path=str(video_path),
                    duration_seconds=duration,
                )

            # Upload
            self.db.update_job_status(job.id, JobStatus.UPLOADING)
            upload_res = youtube_uploader.upload_video(
                video_path=video_path,
                script=script,
                scheduled_publish_time=job.scheduled_time,
            )

            if not upload_res.success:
                raise RuntimeError(upload_res.error_message or "Upload failed on retry")

            completed_job = self.db.update_job_status(
                job.id,
                JobStatus.COMPLETED,
                youtube_id=upload_res.youtube_id,
                youtube_url=upload_res.youtube_url,
            )
            logger.info(f"Job {job.id} succeeded on retry! URL: {upload_res.youtube_url}")
            return completed_job

        except Exception as e:
            err = f"Retry failed: {str(e)}"
            logger.error(err)
            return self.db.update_job_status(job.id, JobStatus.FAILED, error_message=err)

    def retry_all_failed(self, preview_mode: bool = False, backoff_seconds: Optional[int] = None) -> int:
        """Find all eligible failed jobs and retry them."""
        kwargs = {}
        if backoff_seconds is not None:
            kwargs["backoff_seconds"] = backoff_seconds
        failed_jobs = self.db.get_retryable_failed_jobs(**kwargs)
        logger.info(f"Found {len(failed_jobs)} retryable failed jobs.")
        success_count = 0

        for job in failed_jobs:
            retried = self.retry_job(job.id, preview_mode=preview_mode)
            if retried and retried.status == JobStatus.COMPLETED:
                success_count += 1

        return success_count


pipeline = VideoProductionPipeline()
