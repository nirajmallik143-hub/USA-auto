import pytest
from pathlib import Path
from src.config import Settings, VideoFormat, VideoTopic, LLMProvider, TTSEngine


def test_settings_defaults():
    s = Settings(database_url="sqlite:///temp/test.db")
    assert s.daily_shorts_target == 5
    assert s.daily_long_target == 2
    assert s.youtube_made_for_kids is True
    assert s.youtube_dry_run is True
    assert s.timezone == "America/New_York"
    assert s.max_job_retries == 3


def test_auto_detects_runtime_providers_from_available_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "oa")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("TTS_ENGINE", raising=False)
    s = Settings(database_url="sqlite:///temp/test.db")
    assert s.llm_provider == LLMProvider.OPENAI
    assert s.tts_engine == TTSEngine.ELEVENLABS


def test_explicit_provider_overrides_auto_detection(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "oa")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anth")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    s = Settings(database_url="sqlite:///temp/test.db")
    assert s.llm_provider == LLMProvider.ANTHROPIC


def test_video_format_enum():
    assert VideoFormat.SHORTS.value == "shorts"
    assert VideoFormat.LONG.value == "long"


def test_video_topic_enum():
    assert VideoTopic.ANIMAL_RIDDLES.value == "animal_riddles"
    assert VideoTopic.SPACE_FACTS.value == "space_facts"
    assert VideoTopic.MORAL_STORIES.value == "moral_stories"
