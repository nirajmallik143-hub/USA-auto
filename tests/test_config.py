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


def test_video_format_enum():
    assert VideoFormat.SHORTS.value == "shorts"
    assert VideoFormat.LONG.value == "long"


def test_video_topic_enum():
    assert VideoTopic.ANIMAL_RIDDLES.value == "animal_riddles"
    assert VideoTopic.SPACE_FACTS.value == "space_facts"
    assert VideoTopic.MORAL_STORIES.value == "moral_stories"
