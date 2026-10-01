"""
State manager and database interface for tracking jobs, daily quotas, and retries.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import settings
from src.database.models import DailyQuota, JobStatus, VideoJob
from src.logger import logger


class StateManager:
    """Manages persistent SQLite state for video generation jobs and quotas."""

    def __init__(self, db_url: Optional[str] = None):
        url = db_url or settings.database_url
        if url.startswith("sqlite:///"):
            self.db_path = Path(url.replace("sqlite:///", ""))
        else:
            self.db_path = Path(url)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def init_db(self) -> None:
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_jobs (
                    id TEXT PRIMARY KEY,
                    video_format TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    slot_name TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    error_message TEXT,
                    script_data TEXT,
                    video_path TEXT,
                    duration_seconds REAL DEFAULT 0.0,
                    youtube_id TEXT,
                    youtube_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_quotas (
                    date TEXT PRIMARY KEY,
                    target_shorts INTEGER DEFAULT 5,
                    target_long INTEGER DEFAULT 2,
                    completed_shorts INTEGER DEFAULT 0,
                    completed_long INTEGER DEFAULT 0,
                    failed_shorts INTEGER DEFAULT 0,
                    failed_long INTEGER DEFAULT 0
                );
            """)
            conn.commit()

    def create_job(
        self,
        video_format: str,
        topic: str,
        slot_name: str,
        scheduled_time: Optional[str] = None,
        max_retries: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> VideoJob:
        """Create and store a new video job in pending state."""
        j_id = job_id or f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        sched_time = scheduled_time or now
        retries = max_retries if max_retries is not None else settings.max_job_retries

        job = VideoJob(
            id=j_id,
            video_format=video_format,
            topic=topic,
            slot_name=slot_name,
            scheduled_time=sched_time,
            status=JobStatus.PENDING,
            attempt_count=0,
            max_retries=retries,
            created_at=now,
            updated_at=now,
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO video_jobs (
                    id, video_format, topic, slot_name, scheduled_time,
                    status, attempt_count, max_retries, error_message,
                    script_data, video_path, duration_seconds, youtube_id,
                    youtube_url, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.video_format, job.topic, job.slot_name, job.scheduled_time,
                job.status.value, job.attempt_count, job.max_retries, job.error_message,
                None, job.video_path, job.duration_seconds, job.youtube_id,
                job.youtube_url, job.created_at, job.updated_at, job.completed_at
            ))
            conn.commit()

        logger.info(f"Created video job: {job.id} [{job.video_format}] on '{job.topic}' for slot {job.slot_name}")
        return job

    def get_job(self, job_id: str) -> Optional[VideoJob]:
        """Retrieve a video job by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM video_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
        script_data: Optional[Dict[str, Any]] = None,
        video_path: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        youtube_id: Optional[str] = None,
        youtube_url: Optional[str] = None,
        increment_attempt: bool = False,
    ) -> Optional[VideoJob]:
        """Update job status and progress details."""
        now = datetime.now(timezone.utc).isoformat()
        completed_at = now if status == JobStatus.COMPLETED else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch existing to preserve fields
            cursor.execute("SELECT * FROM video_jobs WHERE id = ?", (job_id,))
            existing = cursor.fetchone()
            if not existing:
                return None

            attempts = existing["attempt_count"] + (1 if increment_attempt else 0)
            err = error_message if error_message is not None else existing["error_message"]
            script_json = json.dumps(script_data) if script_data is not None else existing["script_data"]
            v_path = video_path if video_path is not None else existing["video_path"]
            duration = duration_seconds if duration_seconds is not None else existing["duration_seconds"]
            yt_id = youtube_id if youtube_id is not None else existing["youtube_id"]
            yt_url = youtube_url if youtube_url is not None else existing["youtube_url"]
            comp_time = completed_at if completed_at is not None else existing["completed_at"]

            cursor.execute("""
                UPDATE video_jobs SET
                    status = ?,
                    attempt_count = ?,
                    error_message = ?,
                    script_data = ?,
                    video_path = ?,
                    duration_seconds = ?,
                    youtube_id = ?,
                    youtube_url = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
            """, (
                status.value, attempts, err, script_json, v_path,
                duration, yt_id, yt_url, now, comp_time, job_id
            ))
            conn.commit()

        # Update daily quota if status transitioned to completed or failed
        if status == JobStatus.COMPLETED:
            date_str = existing["scheduled_time"][:10]
            self.record_job_completion(date_str, existing["video_format"])
        elif status == JobStatus.FAILED and attempts >= existing["max_retries"]:
            date_str = existing["scheduled_time"][:10]
            self.record_job_failure(date_str, existing["video_format"])

        return self.get_job(job_id)

    def get_pending_jobs(self) -> List[VideoJob]:
        """Get all pending jobs waiting for execution."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM video_jobs WHERE status = ? ORDER BY scheduled_time ASC",
                (JobStatus.PENDING.value,)
            )
            return [self._row_to_job(r) for r in cursor.fetchall()]

    def get_retryable_failed_jobs(self, backoff_seconds: Optional[int] = None) -> List[VideoJob]:
        """
        Get failed jobs that have not exceeded max_retries and have cooled down.
        """
        backoff = backoff_seconds if backoff_seconds is not None else settings.retry_backoff_seconds
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=backoff)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM video_jobs
                WHERE status = ?
                  AND attempt_count < max_retries
                  AND updated_at <= ?
                ORDER BY scheduled_time ASC
            """, (JobStatus.FAILED.value, cutoff))
            return [self._row_to_job(r) for r in cursor.fetchall()]

    def get_all_jobs(self, limit: int = 50) -> List[VideoJob]:
        """Get recent video jobs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM video_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [self._row_to_job(r) for r in cursor.fetchall()]

    def get_jobs_by_date(self, date_str: str) -> List[VideoJob]:
        """Get all jobs scheduled or created for a specific date (YYYY-MM-DD)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM video_jobs WHERE scheduled_time LIKE ? ORDER BY scheduled_time ASC",
                (f"{date_str}%",)
            )
            return [self._row_to_job(r) for r in cursor.fetchall()]

    def get_daily_quota(self, date_str: Optional[str] = None) -> DailyQuota:
        """Get or initialize the daily quota for a given date."""
        target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_quotas WHERE date = ?", (target_date,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO daily_quotas (
                        date, target_shorts, target_long,
                        completed_shorts, completed_long, failed_shorts, failed_long
                    ) VALUES (?, ?, ?, 0, 0, 0, 0)
                """, (target_date, settings.daily_shorts_target, settings.daily_long_target))
                conn.commit()
                return DailyQuota(
                    date=target_date,
                    target_shorts=settings.daily_shorts_target,
                    target_long=settings.daily_long_target,
                )
            return DailyQuota(
                date=row["date"],
                target_shorts=row["target_shorts"],
                target_long=row["target_long"],
                completed_shorts=row["completed_shorts"],
                completed_long=row["completed_long"],
                failed_shorts=row["failed_shorts"],
                failed_long=row["failed_long"],
            )

    def record_job_completion(self, date_str: str, video_format: str) -> None:
        """Increment completed count for a daily quota."""
        # Ensure row exists
        self.get_daily_quota(date_str)
        col = "completed_shorts" if video_format.lower() == "shorts" else "completed_long"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE daily_quotas SET {col} = {col} + 1 WHERE date = ?", (date_str,))
            conn.commit()
        logger.info(f"Recorded completion for {video_format} on {date_str}")

    def record_job_failure(self, date_str: str, video_format: str) -> None:
        """Increment failed count for a daily quota when retries exhausted."""
        self.get_daily_quota(date_str)
        col = "failed_shorts" if video_format.lower() == "shorts" else "failed_long"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE daily_quotas SET {col} = {col} + 1 WHERE date = ?", (date_str,))
            conn.commit()
        logger.warning(f"Recorded permanent failure for {video_format} on {date_str}")

    def can_schedule_more(self, date_str: str, video_format: str) -> bool:
        """Check if quota allows generating another video of this format today."""
        quota = self.get_daily_quota(date_str)
        if video_format.lower() == "shorts":
            return quota.completed_shorts < quota.target_shorts
        return quota.completed_long < quota.target_long

    def _row_to_job(self, row: sqlite3.Row) -> VideoJob:
        script = json.loads(row["script_data"]) if row["script_data"] else None
        return VideoJob(
            id=row["id"],
            video_format=row["video_format"],
            topic=row["topic"],
            slot_name=row["slot_name"],
            scheduled_time=row["scheduled_time"],
            status=JobStatus(row["status"]),
            attempt_count=row["attempt_count"],
            max_retries=row["max_retries"],
            error_message=row["error_message"],
            script_data=script,
            video_path=row["video_path"],
            duration_seconds=row["duration_seconds"],
            youtube_id=row["youtube_id"],
            youtube_url=row["youtube_url"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )


# Global default instance
state_manager = StateManager()
