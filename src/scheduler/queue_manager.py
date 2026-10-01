"""
Queue manager and state tracker for high-volume video generation.
Enforces daily quotas, queues jobs, and monitors retry pipelines.
"""

from datetime import datetime
from typing import Dict, List, Optional
import zoneinfo

from src.config import VideoFormat, settings
from src.database.models import DailyQuota, JobStatus, VideoJob
from src.database.state_manager import StateManager, state_manager
from src.logger import logger
from src.pipeline import VideoProductionPipeline, pipeline as default_pipeline
from src.scheduler.daily_schedule import daily_schedule


class QueueManager:
    """Coordinates execution, state tracking, and quota health across the pipeline."""

    def __init__(self, db: Optional[StateManager] = None, pipeline: Optional[VideoProductionPipeline] = None, pipe: Optional[VideoProductionPipeline] = None):
        self.db = db or state_manager
        self.pipeline = pipeline or pipe or default_pipeline

    def queue_daily_slots(self, target_date: Optional[str] = None) -> List[VideoJob]:
        """
        Pre-register the 7 daily video slots into the database if not already present.
        """
        date_str = target_date or datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
        slots = daily_schedule.get_slots_for_date(date_str)
        existing_jobs = {j.slot_name: j for j in self.db.get_jobs_by_date(date_str)}

        created_jobs = []
        for slot in slots:
            if slot.slot_name in existing_jobs:
                logger.info(f"Slot {slot.slot_name} already queued for {date_str}, skipping.")
                created_jobs.append(existing_jobs[slot.slot_name])
                continue

            scheduled_dt = slot.get_scheduled_datetime(date_str)
            job = self.db.create_job(
                video_format=slot.video_format,
                topic=slot.topic,
                slot_name=slot.slot_name,
                scheduled_time=scheduled_dt.isoformat(),
                job_id=f"job_{date_str}_{slot.slot_name}",
            )
            created_jobs.append(job)

        logger.info(f"Queued {len(created_jobs)} jobs for {date_str} (5 Shorts + 2 Long)")
        return created_jobs

    def execute_slot_job(self, job_id: str, preview_mode: bool = False) -> Optional[VideoJob]:
        """Execute a specific queued job."""
        job = self.db.get_job(job_id)
        if not job:
            logger.error(f"Cannot execute non-existent job: {job_id}")
            return None

        if job.status == JobStatus.COMPLETED:
            logger.info(f"Job {job_id} already completed, skipping.")
            return job

        return self.pipeline.run_job(
            video_format=job.video_format,
            topic=job.topic,
            slot_name=job.slot_name,
            scheduled_time=job.scheduled_time,
            job_id=job.id,
            preview_mode=preview_mode,
            enforce_quota=True,
        )

    def run_daily_batch(self, target_date: Optional[str] = None, preview_mode: bool = False) -> List[VideoJob]:
        """
        Immediately execute all 7 jobs for the target date sequentially.
        Useful for local batch processing or testing full daily quota.
        """
        date_str = target_date or datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
        logger.info(f"Starting daily batch execution for {date_str} (7 jobs)")
        queued = self.queue_daily_slots(date_str)

        results = []
        for job in queued:
            logger.info(f"--- Executing slot: {job.slot_name} [{job.video_format}] on '{job.topic}' ---")
            res = self.execute_slot_job(job.id, preview_mode=preview_mode)
            if res:
                results.append(res)

        # Run retries for any failures immediately
        failed_count = self.pipeline.retry_all_failed(preview_mode=preview_mode)
        if failed_count > 0:
            logger.info(f"Retried and recovered {failed_count} jobs.")

        quota = self.get_quota_status(date_str)
        logger.info(
            f"Daily batch finished for {date_str}. "
            f"Completed Shorts: {quota.completed_shorts}/{quota.target_shorts}, "
            f"Completed Long: {quota.completed_long}/{quota.target_long}"
        )
        return results

    def get_quota_status(self, target_date: Optional[str] = None) -> DailyQuota:
        """Get quota tracking details for today."""
        date_str = target_date or datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
        return self.db.get_daily_quota(date_str)

    def monitor_and_retry(self, preview_mode: bool = False, backoff_seconds: Optional[int] = None) -> int:
        """Poll and trigger retries for failed jobs that have cooled down."""
        return self.pipeline.retry_all_failed(preview_mode=preview_mode, backoff_seconds=backoff_seconds)


queue_manager = QueueManager()
