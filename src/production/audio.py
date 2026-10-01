"""
Kid-friendly background music generator and audio mixer.
Synthesizes gentle, cheerful acoustic/chime background tracks or loads audio assets.
"""

import math
from pathlib import Path
from typing import Optional
import numpy as np
import wave

from src.logger import logger


class BackgroundMusicGenerator:
    """Generates gentle, cheerful royalty-free background music for kids' videos."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def generate_kid_bg_track(self, duration_seconds: float, output_path: Path) -> Path:
        """
        Synthesize a soft, cheerful, looping acoustic marimba/music-box melody
        in C Major pentatonic scale.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        total_samples = int(self.sample_rate * duration_seconds)

        # Frequencies for C major pentatonic (cheerful & pleasant for kids)
        # C4, D4, E4, G4, A4, C5, D5, E5, G5
        notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25, 783.99]

        audio = np.zeros(total_samples, dtype=np.float32)
        beat_duration = 0.5  # 120 bpm, 2 notes per second
        num_beats = int(duration_seconds / beat_duration) + 1

        # Melodic progression pattern
        pattern = [0, 2, 4, 3, 5, 4, 2, 1, 0, 4, 5, 7, 5, 4, 2, 0]

        for beat_idx in range(num_beats):
            note_idx = pattern[beat_idx % len(pattern)]
            freq = notes[note_idx]
            start_sample = int(beat_idx * beat_duration * self.sample_rate)
            note_len = int(beat_duration * 1.8 * self.sample_rate)  # ringing decay

            if start_sample >= total_samples:
                break

            actual_len = min(note_len, total_samples - start_sample)
            t = np.linspace(0, actual_len / self.sample_rate, actual_len, False)

            # Warm bell/marimba harmonics: fundamental + 2nd + 3rd harmonic
            fundamental = np.sin(2 * np.pi * freq * t)
            h2 = 0.3 * np.sin(2 * np.pi * freq * 2.0 * t)
            h3 = 0.15 * np.sin(2 * np.pi * freq * 3.0 * t)
            wave_signal = fundamental + h2 + h3

            # Exponential decay envelope (soft, pleasing music box sound)
            decay = np.exp(-t * 3.5)
            envelope = wave_signal * decay

            # Add softly to audio buffer
            audio[start_sample:start_sample + actual_len] += envelope * 0.25

        # Normalize to prevent clipping, target -18dB RMS
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * 0.45

        # Convert to 16-bit PCM stereo
        pcm_16 = (audio * 32767).astype(np.int16)
        stereo = np.column_stack((pcm_16, pcm_16))

        with wave.open(str(output_path), "w") as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(stereo.tobytes())

        logger.info(f"Synthesized kid background track ({duration_seconds:.1f}s) at {output_path.name}")
        return output_path


bg_music_generator = BackgroundMusicGenerator()
