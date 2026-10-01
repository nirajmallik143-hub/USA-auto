import pytest
from src.config import VideoFormat, VideoTopic
from src.content.script_generator import Scene, ScriptData
from src.youtube.compliance import KidSafetyComplianceValidator
from src.youtube.seo import KidsSEOOptimizer


def test_coppa_compliance_validator_clean_content():
    validator = KidSafetyComplianceValidator()
    result = validator.validate_metadata(
        title="Friendly Forest Animals for Kids! 🦊",
        description="Learn all about friendly animals and kindness in nature! Safe for toddlers.",
        tags=["kids learning", "animals", "preschool"],
        topic=VideoTopic.ANIMAL_RIDDLES.value,
    )
    assert result.is_compliant is True
    assert result.made_for_kids is True
    assert result.category_id in ["15", "27"]


def test_coppa_compliance_validator_blocks_unsafe_terms():
    validator = KidSafetyComplianceValidator()
    # Test with adjacent punctuation (commas, exclamation marks, question marks)
    result = validator.validate_metadata(
        title="Look, a monster! Is it scary?",
        description="A story with blood, fear, and fight.",
        tags=["kids", "stories"],
        topic=VideoTopic.MORAL_STORIES.value,
    )
    assert result.is_compliant is False
    assert any("monster" in r for r in result.reasons)
    assert any("scary" in r for r in result.reasons)
    assert any("blood" in r for r in result.reasons)
    assert any("fight" in r for r in result.reasons)


def test_seo_title_optimizer():
    seo = KidsSEOOptimizer()
    short_title = seo.optimize_title("Can You Guess The Mystery Animal?", VideoFormat.SHORTS.value, "animal_riddles")
    assert "#Shorts" in short_title
    assert len(short_title) <= 70

    long_title = seo.optimize_title("Super Long Episode Title About Space Exploration And Discovering Wonderful Planets In Our Universe", VideoFormat.LONG.value, "space_facts")
    assert len(long_title) <= 85


def test_seo_description_optimizer():
    seo = KidsSEOOptimizer()
    script = ScriptData(
        title="Test Long",
        description="A great kid adventure",
        tags=["kids"],
        video_format=VideoFormat.LONG.value,
        topic=VideoTopic.SPACE_FACTS.value,
        target_duration_seconds=180,
        scenes=[],
        call_to_action="Subscribe!",
        chapters=[
            {"time": "00:00", "title": "Intro"},
            {"time": "01:00", "title": "Blast Off"},
        ],
    )
    desc = seo.optimize_description("A great kid adventure", script)
    assert "TIMESTAMPS:" in desc
    assert "00:00 - Intro" in desc
    assert "COPPA" in desc
    assert "#KidsEducation" in desc
