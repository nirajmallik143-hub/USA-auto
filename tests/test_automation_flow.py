import json
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src import cli, preflight
from src.config import VideoFormat
from src.content.script_generator import script_generator
from src.database.models import JobStatus
from src.database.state_manager import StateManager
from src.pipeline import VideoProductionPipeline
from src.scheduler.queue_manager import QueueManager
from src.youtube.uploader import UploadResult

DATE = "2026-10-01"


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = StateManager(f"sqlite:///{tmp_path}/flow.db")
    pipe = VideoProductionPipeline(db=db)
    qm = QueueManager(db=db, pipeline=pipe)
    mp4 = tmp_path / "v.mp4"
    mp4.write_text("x")
    monkeypatch.setattr("src.pipeline.video_editor.produce_video", lambda *a, **kw: (mp4, 30.0))
    monkeypatch.setattr(cli, "state_manager", db)
    monkeypatch.setattr(cli, "queue_manager", qm)
    return db, pipe, qm


def fake_upload(results):
    it = iter(results)
    return lambda **kw: next(it)


def test_quota_exceeded_defers_job_and_stops_batch(env, monkeypatch):
    db, pipe, qm = env
    ok = UploadResult(success=True, youtube_id="a", youtube_url="u")
    quota = UploadResult(success=False, error_message="quota", error_code="quotaExceeded")
    calls = []

    def upload(**kw):
        calls.append(1)
        return ok if len(calls) == 1 else quota

    monkeypatch.setattr("src.pipeline.youtube_uploader.upload_video", upload)
    results = qm.run_daily_batch(DATE)

    assert len(calls) == 2  # stopped right after the quota error
    assert len(results) == 2
    assert results[0].status == JobStatus.COMPLETED
    assert results[1].status == JobStatus.PENDING
    assert pipe.halt_reason
    ok_day, problems, notes = cli.evaluate_day(DATE)
    assert ok_day and not problems and notes  # partial success is not a failure


def test_second_run_is_idempotent(env, monkeypatch):
    db, pipe, qm = env
    calls = []
    monkeypatch.setattr(
        "src.pipeline.youtube_uploader.upload_video",
        lambda **kw: calls.append(1) or UploadResult(success=True, youtube_id="a", youtube_url="u"),
    )
    qm.run_daily_batch(DATE)
    qm.run_daily_batch(DATE)
    assert len(calls) == 7


def test_count_limits_attempts(env, monkeypatch):
    db, pipe, qm = env
    monkeypatch.setattr(
        "src.pipeline.youtube_uploader.upload_video",
        lambda **kw: UploadResult(success=True, youtube_id="a", youtube_url="u"),
    )
    results = qm.run_daily_batch(DATE, max_videos=2)
    assert len(results) == 2


def test_failed_jobs_make_run_daily_exit_nonzero(env, monkeypatch):
    db, pipe, qm = env
    monkeypatch.setattr(
        "src.pipeline.youtube_uploader.upload_video",
        lambda **kw: UploadResult(success=False, error_message="boom"),
    )

    class FixedDate:
        @staticmethod
        def now(tz=None):
            from datetime import datetime
            return datetime.fromisoformat(f"{DATE}T11:00:00+00:00")

    monkeypatch.setattr(cli, "datetime", FixedDate)
    with pytest.raises(SystemExit) as exc:
        cli.cmd_run_daily_batch(Namespace(preview=True, count=None))
    assert exc.value.code == 1
    ok, problems, _ = cli.evaluate_day(DATE)
    assert not ok and any("boom" in p for p in problems)


def test_status_check_without_jobs_fails(env):
    ok, problems, _ = cli.evaluate_day("2030-01-01")
    assert not ok


def test_cli_uses_configured_timezone_for_today(monkeypatch):
    class FixedDate:
        @staticmethod
        def now(tz=None):
            current = datetime(2026, 10, 3, 1, tzinfo=timezone.utc)
            return current.astimezone(tz) if tz else current

    monkeypatch.setattr(cli, "datetime", FixedDate)
    monkeypatch.setattr("src.cli.settings.timezone", "America/New_York")

    assert cli._today() == "2026-10-02"


def test_retry_defers_quota_limited_job(env, monkeypatch, tmp_path):
    db, pipe, _ = env
    job = db.create_job(VideoFormat.SHORTS.value, "space_facts", "retry_slot", f"{DATE}T08:00:00+00:00")
    script = script_generator.generate_script(VideoFormat.SHORTS.value, "space_facts")
    video = tmp_path / "retry.mp4"
    video.write_text("video")
    db.update_job_status(
        job.id,
        JobStatus.FAILED,
        script_data=script.to_dict(),
        video_path=str(video),
        increment_attempt=True,
    )
    monkeypatch.setattr(
        "src.pipeline.youtube_uploader.upload_video",
        lambda **kw: UploadResult(success=False, error_message="quota", error_code="quotaExceeded"),
    )

    retried = pipe.retry_job(job.id)

    assert retried.status == JobStatus.PENDING
    assert retried.error_message.startswith("Deferred:")
    assert pipe.halt_reason


def test_status_check_writes_summary(env, tmp_path):
    db, pipe, qm = env
    job = db.create_job(VideoFormat.SHORTS.value, "space_facts", "s", f"{DATE}T08:00:00-04:00")
    db.update_job_status(job.id, JobStatus.FAILED, error_message="kaput")
    out = tmp_path / "sum.md"
    assert cli.report_day(DATE, str(out)) is False
    assert "kaput" in out.read_text()


def test_doctor_reports_missing_ffmpeg(monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
    results = preflight.run_doctor()
    assert any(r.name == "ffmpeg" and not r.ok for r in results)
    with pytest.raises(SystemExit):
        cli.cmd_doctor(Namespace())


def test_doctor_checks_configured_ffmpeg_binary(monkeypatch):
    checked = []
    monkeypatch.setenv("FFMPEG_BINARY", "/data/data/app/ffmpeg")

    def find_binary(binary):
        checked.append(binary)
        return binary

    monkeypatch.setattr(preflight.shutil, "which", find_binary)

    result = preflight.check_ffmpeg()

    assert checked == ["/data/data/app/ffmpeg"]
    assert result.ok
    assert "found at /data/data/app/ffmpeg" == result.message


def test_doctor_live_requires_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(preflight.settings, "youtube_dry_run", False)
    monkeypatch.setattr(preflight.settings, "youtube_client_secrets_file", tmp_path / "a.json")
    monkeypatch.setattr(preflight.settings, "youtube_credentials_file", tmp_path / "b.json")
    results = preflight.run_doctor()
    assert any(r.name.startswith("youtube token") and not r.ok for r in results)


def test_write_credentials_script(tmp_path):
    secret = {"installed": {"client_id": "x", "note": "it's \"quoted\""}}
    token = {"token": "t", "refresh_token": "r"}
    env = {
        "YOUTUBE_CLIENT_SECRETS_JSON": json.dumps(secret),
        "YOUTUBE_TOKEN_JSON": json.dumps(token),
        "YOUTUBE_CLIENT_SECRETS_FILE": str(tmp_path / "s" / "cs.json"),
        "YOUTUBE_CREDENTIALS_FILE": str(tmp_path / "s" / "tok.json"),
        "PATH": "/usr/bin:/bin",
    }
    root = Path(__file__).resolve().parent.parent
    run = subprocess.run([sys.executable, str(root / "scripts" / "write_credentials.py")], env=env, capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads((tmp_path / "s" / "tok.json").read_text()) == token
    assert "refresh_token" not in run.stdout

    env["YOUTUBE_TOKEN_JSON"] = "{not json"
    bad = subprocess.run([sys.executable, str(root / "scripts" / "write_credentials.py")], env=env, capture_output=True, text=True)
    assert bad.returncode == 1 and "not json" not in bad.stdout
