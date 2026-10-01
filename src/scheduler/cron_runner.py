"""
Standalone continuous scheduler using APScheduler.
Schedules the 7 daily jobs at their configured times and runs periodic retry checks.
"""

from datetime import datetime
from typing import Optional
import zoneinfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings
from src.logger import logger
from src.scheduler.daily_schedule import daily_schedule
from src.scheduler.queue_manager import queue_manager


def _job_slot_trigger(slot_name: str, video_format: str):
    """Callback function executed when a daily slot triggers."""
    date_str = datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
    job_id = f"job_{date_str}_{slot_name}"
    logger.info(f"[SCHEDULER TRIGGER] Running slot {slot_name} ({job_id})")

    # Queue slot if not already registered
    queue_manager.queue_daily_slots(date_str)
    # Execute
    queue_manager.execute_slot_job(job_id)


def _retry_trigger():
    """Periodic callback to inspect and retry any failed jobs."""
    if settings.auto_retry_failed:
        logger.debug("[SCHEDULER] Checking for failed jobs to retry...")
        recovered = queue_manager.monitor_and_retry()
        if recovered > 0:
            logger.info(f"[SCHEDULER] Successfully recovered {recovered} failed jobs on retry.")


def _midnight_queue_trigger():
    """Runs at 00:01 daily to prepare the day's 7 slots in advance."""
    date_str = datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
    logger.info(f"[SCHEDULER] Midnight pre-queueing 7 slots for {date_str}")
    queue_manager.queue_daily_slots(date_str)


class StandaloneScheduler:
    """Manages continuous cron-based scheduling using APScheduler."""

    def __init__(self, blocking: bool = False):
        self.blocking = blocking
        self.scheduler = BlockingScheduler() if blocking else BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        """Register the 7 daily slots and periodic tasks with APScheduler."""
        tz = zoneinfo.ZoneInfo(settings.timezone)

        # 1. Register 7 daily slots
        # Default daily slot times: 08:00, 10:00, 12:00, 14:30, 16:30, 18:30, 20:30
        slots = daily_schedule.get_slots_for_date()
        for slot in slots:
            hour, minute = map(int, slot.time_str.split(":"))
            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self.scheduler.add_job(
                _job_slot_trigger,
                trigger=trigger,
                args=[slot.slot_name, slot.video_format],
                id=f"cron_slot_{slot.slot_name}",
                name=f"Daily Slot: {slot.slot_name} ({slot.time_str})",
                replace_existing=True,
            )
            logger.info(f"Registered scheduler slot: {slot.slot_name} at {slot.time_str} {settings.timezone}")

        # 2. Register periodic retry watcher (runs every 5 minutes)
        self.scheduler.add_job(
            _retry_trigger,
            trigger=IntervalTrigger(minutes=5),
            id="periodic_retry_watcher",
            name="Periodic Failed Job Retry Watcher",
            replace_existing=True,
        )

        # 3. Register midnight pre-queue job (runs every day at 00:01)
        self.scheduler.add_job(
            _midnight_queue_trigger,
            trigger=CronTrigger(hour=0, minute=1, timezone=tz),
            id="midnight_queue_job",
            name="Midnight Daily Slots Pre-queue",
            replace_existing=True,
        )

    def start(self) -> None:
        """Start the scheduler."""
        logger.info(f"Starting StandaloneScheduler (Timezone: {settings.timezone})")
        # Pre-queue today's slots immediately on startup
        date_str = datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
        queue_manager.queue_daily_slots(date_str)
        self.scheduler.start()

    def shutdown(self) -> None:
        """Stop the scheduler cleanly."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")
