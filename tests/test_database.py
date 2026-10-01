import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.database.models import JobStatus, VideoJob
from src.database.state_manager import StateManager


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    return StateManager(f"sqlite:///{db_file}")


def test_create_and_get_job(temp_db):
    job = temp_db.create_job(
        video_format="shorts",
        topic="animal_riddles",
        slot_name="slot_1_morning_short",
    )
    assert job.id.startswith("job_")
    assert job.status == JobStatus.PENDING
    assert job.attempt_count == 0

    fetched = temp_db.get_job(job.id)
    assert fetched is not None
    assert fetched.id == job.id
    assert fetched.video_format == "shorts"
    assert fetched.topic == "animal_riddles"


def test_update_job_status_and_quota(temp_db):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    job = temp_db.create_job(
        video_format="shorts",
        topic="animal_riddles",
        slot_name="slot_1_morning_short",
        scheduled_time=f"{today}T08:00:00",
    )

    # Initial quota
    q1 = temp_db.get_daily_quota(today)
    assert q1.completed_shorts == 0

    # Advance status through pipeline
    temp_db.update_job_status(job.id, JobStatus.GENERATING_SCRIPT, increment_attempt=True)
    j2 = temp_db.get_job(job.id)
    assert j2.status == JobStatus.GENERATING_SCRIPT
    assert j2.attempt_count == 1

    temp_db.update_job_status(
        job.id,
        JobStatus.COMPLETED,
        youtube_id="mock_yt_123",
        youtube_url="https://youtube.com/watch?v=mock_yt_123",
        duration_seconds=42.5,
    )
    j3 = temp_db.get_job(job.id)
    assert j3.status == JobStatus.COMPLETED
    assert j3.youtube_id == "mock_yt_123"
    assert j3.duration_seconds == 42.5

    # Check quota incremented
    q2 = temp_db.get_daily_quota(today)
    assert q2.completed_shorts == 1
    assert q2.completed_long == 0


def test_retryable_failed_jobs(temp_db):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    job = temp_db.create_job(
        video_format="long",
        topic="space_facts",
        slot_name="slot_2_morning_long",
        scheduled_time=f"{today}T10:00:00",
        max_retries=3,
    )

    # Mark as failed with 1 attempt
    temp_db.update_job_status(
        job.id,
        JobStatus.FAILED,
        error_message="Network timeout during LLM call",
        increment_attempt=True,
    )

    # With 0 backoff, it should be immediately retryable
    retryable = temp_db.get_retryable_failed_jobs(backoff_seconds=0)
    assert len(retryable) == 1
    assert retryable[0].id == job.id

    # If attempts reach max_retries, it should no longer be retryable
    temp_db.update_job_status(job.id, JobStatus.FAILED, increment_attempt=True)
    temp_db.update_job_status(job.id, JobStatus.FAILED, increment_attempt=True)
    j_exhausted = temp_db.get_job(job.id)
    assert j_exhausted.attempt_count == 3

    assert len(temp_db.get_retryable_failed_jobs(backoff_seconds=0)) == 0


def test_can_schedule_more(temp_db):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert temp_db.can_schedule_more(today, "shorts") is True
    assert temp_db.can_schedule_more(today, "long") is True

    # Simulate completing 5 shorts
    for _ in range(5):
        temp_db.record_job_completion(today, "shorts")
    assert temp_db.can_schedule_more(today, "shorts") is False

    # Long is still available
    assert temp_db.can_schedule_more(today, "long") is True
    temp_db.record_job_completion(today, "long")
    temp_db.record_job_completion(today, "long")
    assert temp_db.can_schedule_more(today, "long") is False
