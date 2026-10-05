"""
Celery distributed worker and task queue integration for cloud deployment.
Enables asynchronous job execution, worker pools, and Celery Beat scheduling.
"""

from datetime import datetime
from typing import Optional
import zoneinfo
from celery import Celery
from celery.schedules import crontab

from src.config import VideoFormat, settings
from src.logger import logger
from src.pipeline import pipeline
from src.scheduler.daily_schedule import daily_schedule
from src.scheduler.queue_manager import queue_manager

celery_app = Celery(
    "video_pipeline",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minute hard ceiling for long renders
)


@celery_app.task(name="tasks.execute_video_job", bind=True, max_retries=settings.max_job_retries)
def execute_video_job_task(
    self,
    video_format: str,
    topic: Optional[str] = None,
    slot_name: str = "celery_slot",
    scheduled_time: Optional[str] = None,
    job_id: Optional[str] = None,
):
    """Celery task to execute a full video generation and upload job."""
    logger.info(f"[Celery] Executing video job task for format={video_format}, topic={topic}")
    try:
        job = pipeline.run_job(
            video_format=video_format,
            topic=topic,
            slot_name=slot_name,
            scheduled_time=scheduled_time,
            job_id=job_id,
        )
        return {"job_id": job.id, "status": job.status.value, "youtube_id": job.youtube_id}
    except Exception as exc:
        logger.error(f"[Celery] Error in execute_video_job_task: {exc}")
        # Automatic Celery retry with backoff
        raise self.retry(exc=exc, countdown=settings.retry_backoff_seconds)


@celery_app.task(name="tasks.run_slot")
def run_slot_task(slot_name: str, video_format: str):
    """Celery task invoked by Celery Beat for a scheduled daily slot."""
    date_str = datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
    job_id = f"job_{date_str}_{slot_name}"
    logger.info(f"[Celery Beat] Triggered slot: {slot_name} ({job_id})")
    queue_manager.queue_daily_slots(date_str)
    res = queue_manager.execute_slot_job(job_id)
    return {"job_id": job_id, "status": res.status.value if res else "unknown"}


@celery_app.task(name="tasks.retry_failed_jobs")
def retry_failed_jobs_task():
    """Periodic Celery task to monitor and retry failed jobs."""
    recovered = queue_manager.monitor_and_retry()
    logger.info(f"[Celery Beat] Retried and recovered {recovered} failed jobs.")
    return {"recovered": recovered}


@celery_app.task(name="tasks.queue_daily_slots")
def queue_daily_slots_task():
    """Midnight task to pre-register the 7 slots for the day."""
    date_str = datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
    jobs = queue_manager.queue_daily_slots(date_str)
    return {"date": date_str, "queued_count": len(jobs)}


# Configure Celery Beat from the same slot definitions as the standalone scheduler.
beat_schedule = {
    f"slot-{slot.slot_name}": {
        "task": "tasks.run_slot",
        "schedule": crontab(
            hour=int(slot.time_str.split(":")[0]),
            minute=int(slot.time_str.split(":")[1]),
        ),
        "args": (slot.slot_name, slot.video_format),
    }
    for slot in daily_schedule.get_slots_for_date()
}
beat_schedule.update({
    # Periodic retry watcher every 5 minutes
    "periodic-retry-failed-jobs": {
        "task": "tasks.retry_failed_jobs",
        "schedule": crontab(minute="*/5"),
    },
    # Midnight queue setup at 00:01
    "midnight-queue-daily-slots": {
        "task": "tasks.queue_daily_slots",
        "schedule": crontab(hour=0, minute=1),
    },
})

celery_app.conf.beat_schedule = beat_schedule
