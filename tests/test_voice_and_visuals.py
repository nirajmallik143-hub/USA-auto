import pytest
import subprocess
from pathlib import Path
from types import SimpleNamespace
from PIL import Image

from src.config import VideoFormat, VideoTopic
from src.production.audio import BackgroundMusicGenerator
from src.production.subtitles import SubtitleGenerator
from src.production.visuals import ProceduralKidBackgroundGenerator
from src.production import voice
from src.production.voice import VoiceEngine


def test_voice_engine_clean_narration():
    ve = VoiceEngine()
    raw = "[Happy giggle] Look at the puppy! (claps hands) Wow!"
    cleaned = ve._clean_narration_text(raw)
    assert cleaned == "Look at the puppy!  Wow!"


def test_offline_voice_uses_configured_ffmpeg(monkeypatch, tmp_path):
    output_path = tmp_path / "voice.mp3"
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        output_path.write_bytes(b"audio")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(voice, "FFMPEG_BINARY", "/app/files/ffmpeg")
    monkeypatch.setattr(subprocess, "run", run)
    engine = VoiceEngine()
    monkeypatch.setattr(engine, "_get_audio_duration", lambda path: 1.0)

    result = engine._synthesize_offline("Hello there!", output_path)

    assert result.engine_used == "flite_offline"
    assert commands[0][0] == "/app/files/ffmpeg"


def test_procedural_background_generation(tmp_path):
    gen = ProceduralKidBackgroundGenerator()

    # Test Shorts (9:16)
    out_shorts = tmp_path / "test_shorts.png"
    gen.generate_scene_image(
        video_format=VideoFormat.SHORTS.value,
        topic=VideoTopic.SPACE_FACTS.value,
        scene_index=0,
        scene_text="Blast Off!",
        output_path=out_shorts,
    )
    assert out_shorts.exists()
    with Image.open(out_shorts) as img:
        assert img.size == (1080, 1920)

    # Test Long (16:9)
    out_long = tmp_path / "test_long.png"
    gen.generate_scene_image(
        video_format=VideoFormat.LONG.value,
        topic=VideoTopic.ANIMAL_RIDDLES.value,
        scene_index=1,
        scene_text="Clue #1",
        output_path=out_long,
    )
    assert out_long.exists()
    with Image.open(out_long) as img:
        assert img.size == (1920, 1080)


def test_subtitle_overlay_creation(tmp_path):
    sub = SubtitleGenerator()
    out_sub = tmp_path / "sub_overlay.png"
    sub.create_caption_overlay(
        text="Guess the mystery animal now!",
        video_format=VideoFormat.SHORTS.value,
        output_path=out_sub,
    )
    assert out_sub.exists()
    with Image.open(out_sub) as img:
        assert img.size == (1080, 1920)
        assert img.mode == "RGBA"


def test_bg_music_synthesis(tmp_path):
    bgm = BackgroundMusicGenerator(sample_rate=22050)
    out_wav = tmp_path / "test_bgm.wav"
    bgm.generate_kid_bg_track(duration_seconds=2.0, output_path=out_wav)
    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000
