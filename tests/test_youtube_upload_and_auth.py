import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httplib2
import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from src.config import Settings, VideoFormat, VideoTopic
from src.content.script_generator import script_generator
from src.youtube import client as yt_client
from src.youtube.client import MockYouTubeClient, YouTubeAuthError
from src.youtube.uploader import (
    YouTubeUploader,
    resolve_publish_at,
    validate_description,
    validate_tags,
    validate_title,
)


def http_error(status, reason="backendError"):
    body = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()
    return HttpError(httplib2.Response({"status": status}), body)


class FakeRequest:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def next_chunk(self):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return None, outcome


class FakeClient:
    def __init__(self, outcomes):
        self.request = FakeRequest(outcomes)
        self.body = None

    def videos(self):
        return self

    def insert(self, part, body, media_body):
        self.body = body
        return self.request


@pytest.fixture
def video_file(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"data")
    return f


@pytest.fixture
def script():
    return script_generator.generate_script(VideoFormat.SHORTS.value, VideoTopic.SPACE_FACTS.value)


def make_uploader(outcomes):
    sleeps = []
    client = FakeClient(outcomes)
    return YouTubeUploader(client=client, sleep=sleeps.append), client, sleeps


def test_config_env_aliases(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "procedural")
    monkeypatch.setenv("DRY_RUN_UPLOAD", "false")
    monkeypatch.setenv("TTS_PROVIDER", "gtts")
    monkeypatch.setenv("COPPA_MADE_FOR_KIDS", "true")
    s = Settings()
    assert s.llm_provider.value == "template"
    assert s.youtube_dry_run is False
    assert s.tts_engine.value == "gtts"
    assert s.youtube_made_for_kids is True


def test_metadata_validation_limits():
    assert len(validate_title("x" * 300)) <= 100
    assert validate_title("   ") != ""
    desc = validate_description("é" * 5000)
    assert len(desc.encode("utf-8")) <= 5000
    tags = validate_tags([f"tag number {i:03d}" for i in range(200)])
    assert 0 < len(tags) < 200
    assert sum(len(t) + 2 for t in tags) + len(tags) <= 500


def test_resolve_publish_at():
    future = datetime.now(timezone.utc) + timedelta(hours=3)
    assert resolve_publish_at(future.isoformat()).endswith("Z")
    assert resolve_publish_at(future.replace(tzinfo=None).isoformat()).endswith("Z")
    assert resolve_publish_at((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()) is None
    assert resolve_publish_at("garbage") is None
    assert resolve_publish_at(None) is None


def test_upload_retries_5xx_with_backoff(video_file, script):
    uploader, client, sleeps = make_uploader([http_error(503), ConnectionError("reset"), {"id": "abc123"}])
    res = uploader.upload_video(video_file, script)
    assert res.success and res.youtube_id == "abc123"
    assert client.request.calls == 3
    assert len(sleeps) == 2 and sleeps[0] < 2 <= sleeps[1]


def test_upload_gives_up_after_max_retries(video_file, script):
    uploader, _, _ = make_uploader([http_error(500)] * 20)
    res = uploader.upload_video(video_file, script)
    assert not res.success and not res.should_halt


@pytest.mark.parametrize("reason", ["quotaExceeded", "uploadLimitExceeded"])
def test_upload_quota_errors_halt(video_file, script, reason):
    uploader, _, sleeps = make_uploader([http_error(403, reason)])
    res = uploader.upload_video(video_file, script)
    assert not res.success
    assert res.error_code == reason and res.should_halt
    assert sleeps == []


def test_upload_body_kids_and_schedule(video_file, script, monkeypatch):
    monkeypatch.setattr("src.youtube.uploader.settings.youtube_privacy_status", "scheduled")
    future = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    uploader, client, _ = make_uploader([{"id": "x"}])
    res = uploader.upload_video(video_file, script, scheduled_publish_time=future)
    status = client.body["status"]
    assert res.success
    assert status["selfDeclaredMadeForKids"] is True
    assert "madeForKids" not in status
    assert status["privacyStatus"] == "private"
    assert status["publishAt"].endswith("Z")
    assert len(client.body["snippet"]["title"]) <= 100


def test_upload_without_future_slot_uses_valid_privacy(video_file, script, monkeypatch):
    monkeypatch.setattr("src.youtube.uploader.settings.youtube_privacy_status", "scheduled")
    past = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    uploader, client, _ = make_uploader([{"id": "x"}])
    uploader.upload_video(video_file, script, scheduled_publish_time=past)
    assert client.body["status"]["privacyStatus"] == "public"
    assert "publishAt" not in client.body["status"]


def test_auth_error_is_reported_as_auth(video_file, script):
    class BadUploader(YouTubeUploader):
        @property
        def client(self):
            raise YouTubeAuthError("token revoked")

    res = BadUploader().upload_video(video_file, script)
    assert res.error_code == "auth" and res.should_halt


def test_get_client_dry_run_returns_mock(monkeypatch):
    monkeypatch.setattr(yt_client.settings, "youtube_dry_run", True)
    assert isinstance(yt_client.get_youtube_client(), MockYouTubeClient)


def test_get_client_live_missing_token_fails_loudly(monkeypatch, tmp_path):
    monkeypatch.setattr(yt_client.settings, "youtube_dry_run", False)
    monkeypatch.setattr(yt_client.settings, "youtube_credentials_file", tmp_path / "nope.json")
    with pytest.raises(YouTubeAuthError, match="auth"):
        yt_client.get_youtube_client()


def _write_token(path):
    path.write_text(json.dumps({
        "token": "old", "refresh_token": "r", "client_id": "c", "client_secret": "s",
        "token_uri": "https://oauth2.googleapis.com/token",
        "expiry": "2000-01-01T00:00:00Z",
    }))


def test_invalid_grant_gives_actionable_error(monkeypatch, tmp_path):
    token = tmp_path / "t.json"
    _write_token(token)

    def boom(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.")

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", boom)
    with pytest.raises(YouTubeAuthError) as exc:
        yt_client.load_credentials(token)
    msg = str(exc.value)
    assert "invalid_grant" in msg and "In production" in msg and "auth" in msg


def test_refreshed_token_is_persisted(monkeypatch, tmp_path):
    token = tmp_path / "t.json"
    _write_token(token)

    def fake_refresh(self, request):
        self.token = "new-access-token"
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", fake_refresh)
    creds = yt_client.load_credentials(token)
    assert creds.token == "new-access-token"
    assert json.loads(token.read_text())["token"] == "new-access-token"
