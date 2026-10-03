"""
Text-to-Speech (TTS) engine integration supporting ElevenLabs and gTTS.
Produces engaging, kid-friendly American voiceovers with automatic fallback.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional
import requests
from gtts import gTTS
from moviepy import AudioFileClip
from moviepy.config import FFMPEG_BINARY

from src.config import TTSEngine, settings
from src.logger import logger


@dataclass
class AudioResult:
    audio_path: Path
    duration_seconds: float
    engine_used: str


@dataclass
class SceneAudio:
    scene_index: int
    audio_path: Path
    duration_seconds: float
    caption_text: str


class VoiceEngine:
    """Manages text-to-speech voice generation with ElevenLabs and gTTS."""

    def __init__(self, engine: Optional[TTSEngine] = None):
        self.engine = engine or settings.tts_engine

    def generate_speech(self, text: str, output_path: Path) -> AudioResult:
        """
        Generate voiceover audio file from text.
        Attempts ElevenLabs first if selected, falling back to gTTS on failure.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        clean_text = self._clean_narration_text(text)

        if self.engine == TTSEngine.ELEVENLABS and settings.elevenlabs_api_key:
            try:
                res = self._synthesize_elevenlabs(clean_text, output_path)
                logger.info(f"ElevenLabs TTS succeeded ({res.duration_seconds:.1f}s): {output_path.name}")
                return res
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed ({e}), falling back to gTTS")

        # Fallback to gTTS (Google Text-to-Speech, free & US English accent)
        try:
            res = self._synthesize_gtts(clean_text, output_path)
            logger.info(f"gTTS voiceover succeeded ({res.duration_seconds:.1f}s): {output_path.name}")
            return res
        except Exception as e:
            logger.warning(f"gTTS voiceover failed ({e}), falling back to offline synthesizer")
            return self._synthesize_offline(clean_text, output_path)

    def generate_scenes_speech(self, scenes: List[Any], job_temp_dir: Path) -> List[SceneAudio]:
        """
        Generate separate audio files for each scene in the script.
        Ensures exact audio-to-visual synchronization.
        """
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for i, scene in enumerate(scenes):
            scene_path = job_temp_dir / f"scene_{i:02d}.mp3"
            audio_res = self.generate_speech(scene.narration, scene_path)
            results.append(
                SceneAudio(
                    scene_index=i,
                    audio_path=audio_res.audio_path,
                    duration_seconds=audio_res.duration_seconds,
                    caption_text=scene.caption_text,
                )
            )

        return results

    def _clean_narration_text(self, text: str) -> str:
        """Strip brackets, stage directions, and extraneous symbols."""
        import re
        # Remove bracketed sound effects like [Roar!], [Laughter]
        cleaned = re.sub(r"\[.*?\]", "", text)
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        return cleaned.strip()

    def _synthesize_elevenlabs(self, text: str, output_path: Path) -> AudioResult:
        voice_id = settings.elevenlabs_voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": settings.elevenlabs_model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.35,  # Expressive, cheerful tone
                "use_speaker_boost": True,
            },
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(resp.content)

        duration = self._get_audio_duration(output_path)
        return AudioResult(audio_path=output_path, duration_seconds=duration, engine_used="elevenlabs")

    def _synthesize_gtts(self, text: str, output_path: Path) -> AudioResult:
        # tld="com" provides US English accent, lang="en"
        tts = gTTS(text=text, lang="en", tld="com", slow=False)
        tts.save(str(output_path))
        duration = self._get_audio_duration(output_path)
        return AudioResult(audio_path=output_path, duration_seconds=duration, engine_used="gtts")

    def _synthesize_offline(self, text: str, output_path: Path) -> AudioResult:
        """
        Offline fallback text-to-speech using FFmpeg libflite or tone synthesizer.
        Ensures pipeline generates valid audio even when network is unavailable.
        """
        import subprocess
        import re
        safe_text = re.sub(r"[^a-zA-Z0-9\s.,?!]", " ", text).strip()
        if not safe_text:
            safe_text = "Welcome to our video!"

        # Try FFmpeg flite filter first
        try:
            cmd = [
                FFMPEG_BINARY, "-y", "-f", "lavfi",
                "-i", f"flite=text='{safe_text}':voice=kal",
                "-q:a", "2", str(output_path)
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                duration = self._get_audio_duration(output_path)
                return AudioResult(audio_path=output_path, duration_seconds=duration, engine_used="flite_offline")
        except Exception as e:
            logger.warning(f"Flite TTS synthesis failed ({e}), falling back to tone generator")

        # Secondary fallback: generate spoken-cadence tone matching word duration
        # Assuming ~130 words per minute for kids narration (~2.2 words/sec)
        words = len(text.split())
        est_duration = max(2.5, words / 2.2)
        try:
            cmd = [
                FFMPEG_BINARY, "-y", "-f", "lavfi",
                "-i", f"sine=frequency=392:duration={est_duration:.2f}",
                "-af", "volume=0.2",
                "-q:a", "2", str(output_path)
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=20)
            return AudioResult(audio_path=output_path, duration_seconds=est_duration, engine_used="tone_offline")
        except Exception as e:
            logger.error(f"Failed to generate offline audio: {e}")
            raise

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Measure audio duration via MoviePy AudioFileClip."""
        try:
            with AudioFileClip(str(audio_path)) as clip:
                return float(clip.duration)
        except Exception as e:
            logger.warning(f"Error measuring audio duration ({e}), estimating from file size")
            # Fallback estimation: MP3 at 128kbps ~ 16KB/s
            size = os.path.getsize(audio_path)
            return max(1.0, size / 16000.0)


voice_engine = VoiceEngine()
