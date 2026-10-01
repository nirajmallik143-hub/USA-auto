import pytest
from pathlib import Path
from src.config import VideoFormat, VideoTopic
from src.database.models import JobStatus
from src.database.state_manager import StateManager
from src.pipeline import VideoProductionPipeline
from src.scheduler.daily_schedule import DailyScheduleManager
from src.scheduler.queue_manager import QueueManager
from src.youtube.uploader import YouTubeUploader, UploadResult


def test_daily_schedule_slots_generation():
    mgr = DailyScheduleManager()
    slots = mgr.get_slots_for_date("2026-10-01")
    assert len(slots) == 7

    formats = [s.video_format for s in slots]
    assert formats.count(VideoFormat.SHORTS.value) == 5
    assert formats.count(VideoFormat.LONG.value) == 2

    # Check times
    expected_times = ["08:00", "10:00", "12:00", "14:30", "16:30", "18:30", "20:30"]
    assert [s.time_str for s in slots] == expected_times


def test_queue_manager_queues_all_slots(tmp_path):
    db = StateManager(f"sqlite:///{tmp_path}/queue_test.db")
    qm = QueueManager(db=db)

    jobs = qm.queue_daily_slots("2026-10-01")
    assert len(jobs) == 7
    assert all(j.status == JobStatus.PENDING for j in jobs)

    # Calling again should not duplicate
    jobs2 = qm.queue_daily_slots("2026-10-01")
    assert len(jobs2) == 7
    assert len(db.get_jobs_by_date("2026-10-01")) == 7


def test_pipeline_dry_run_execution(tmp_path, monkeypatch):
    db = StateManager(f"sqlite:///{tmp_path}/pipe_test.db")
    pipe = VideoProductionPipeline(db=db)

    # Mock video editor to return a mock file quickly without long encoding
    mock_mp4 = tmp_path / "mock_video.mp4"
    mock_mp4.write_text("dummy video content")

    def mock_produce(*args, **kwargs):
        return mock_mp4, 35.0

    monkeypatch.setattr("src.pipeline.video_editor.produce_video", mock_produce)

    job = pipe.run_job(
        video_format=VideoFormat.SHORTS.value,
        topic=VideoTopic.ANIMAL_RIDDLES.value,
        slot_name="test_slot_1",
        preview_mode=True,
    )

    assert job.status == JobStatus.COMPLETED
    assert job.youtube_id is not None
    assert job.duration_seconds == 35.0
    assert job.attempt_count == 1

    # Verify quota recorded
    today = job.scheduled_time[:10]
    quota = db.get_daily_quota(today)
    assert quota.completed_shorts == 1


def test_pipeline_retry_mechanism(tmp_path, monkeypatch):
    db = StateManager(f"sqlite:///{tmp_path}/retry_test.db")
    pipe = VideoProductionPipeline(db=db)

    call_count = 0

    def mock_produce_fail_then_pass(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Temporary encoder crash")
        mock_mp4 = tmp_path / "recovered.mp4"
        mock_mp4.write_text("recovered video")
        return mock_mp4, 40.0

    monkeypatch.setattr("src.pipeline.video_editor.produce_video", mock_produce_fail_then_pass)

    # First attempt fails
    failed_job = pipe.run_job(
        video_format=VideoFormat.SHORTS.value,
        topic=VideoTopic.KIDS_JOKES_PUZZLES.value,
        slot_name="retry_slot",
        enforce_quota=False,
    )
    assert failed_job.status == JobStatus.FAILED
    assert "Temporary encoder crash" in failed_job.error_message
    assert failed_job.attempt_count == 1

    # Retry should succeed
    retried_job = pipe.retry_job(failed_job.id)
    assert retried_job.status == JobStatus.COMPLETED
    assert retried_job.youtube_id is not None
