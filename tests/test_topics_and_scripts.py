import pytest
from src.config import VideoFormat, VideoTopic
from src.content.topics import TOPIC_CATALOG, get_topic_definition
from src.content.topic_rotator import TopicRotator
from src.content.script_generator import ProceduralKidsTemplateEngine, ScriptGenerator


def test_topic_catalog_completeness():
    required_topics = [
        VideoTopic.ANIMAL_RIDDLES.value,
        VideoTopic.MORAL_STORIES.value,
        VideoTopic.ALPHABET_NUMBER_LEARNING.value,
        VideoTopic.SPACE_FACTS.value,
        VideoTopic.DINOSAUR_ADVENTURES.value,
        VideoTopic.SCIENCE_CURIOSITIES.value,
        VideoTopic.KIDS_JOKES_PUZZLES.value,
    ]
    for topic_id in required_topics:
        assert topic_id in TOPIC_CATALOG
        defn = get_topic_definition(topic_id)
        assert defn.name
        assert defn.educational_goal
        assert len(defn.keywords) > 0
        assert len(defn.color_palette) > 0


def test_topic_rotator_7_daily_slots():
    rotator = TopicRotator()
    slots = rotator.get_daily_schedule_topics("2026-10-01")

    assert len(slots) == 7

    # Count formats
    shorts_slots = [s for s in slots if s["format"] == VideoFormat.SHORTS.value]
    long_slots = [s for s in slots if s["format"] == VideoFormat.LONG.value]

    assert len(shorts_slots) == 5
    assert len(long_slots) == 2

    # Check times are ordered
    times = [s["time"] for s in slots]
    assert times == ["08:00", "10:00", "12:00", "14:30", "16:30", "18:30", "20:30"]

    # Check the two long video topics are distinct
    assert long_slots[0]["topic"] != long_slots[1]["topic"]


def test_procedural_shorts_script_constraints():
    engine = ProceduralKidsTemplateEngine()
    for topic in [VideoTopic.ANIMAL_RIDDLES.value, VideoTopic.SPACE_FACTS.value, VideoTopic.KIDS_JOKES_PUZZLES.value]:
        script = engine.generate_shorts_script(topic)
        assert script.video_format == VideoFormat.SHORTS.value
        # Duration under 60 seconds
        assert script.target_duration_seconds < 60.0
        # Word count suitable for 30-50s
        assert 30 <= script.total_words <= 150
        assert len(script.scenes) >= 3
        assert "#Shorts" in script.title
        assert len(script.tags) > 0


def test_procedural_long_script_constraints():
    engine = ProceduralKidsTemplateEngine()
    for topic in [VideoTopic.MORAL_STORIES.value, VideoTopic.SPACE_FACTS.value]:
        script = engine.generate_long_script(topic)
        assert script.video_format == VideoFormat.LONG.value
        # Long script target duration between 120s (2m) and 480s (8m)
        assert script.target_duration_seconds >= 120.0
        assert script.total_words >= 150
        assert len(script.scenes) >= 5
        assert script.chapters is not None
        assert len(script.chapters) >= 4


def test_script_generator_fallback(monkeypatch):
    gen = ScriptGenerator()
    script = gen.generate_script(VideoFormat.SHORTS.value, VideoTopic.ANIMAL_RIDDLES.value)
    assert script.video_format == VideoFormat.SHORTS.value
    assert len(script.scenes) > 0
