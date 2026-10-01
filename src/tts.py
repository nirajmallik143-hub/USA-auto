import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_voiceover(text: str, output_path: str, provider: Optional[str] = None) -> str:
    """
    Synthesizes speech from text and saves it as an MP3 file.
    Args:
        text (str): Spoken content.
        output_path (str): Destination file path (should end in .mp3).
        provider (str, optional): "gtts" or "openai". Defaults to env TTS_PROVIDER or "gtts".
    Returns:
        str: Absolute path to the generated audio file.
    """
    if not provider:
        provider = os.getenv("TTS_PROVIDER", "gtts").lower()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info(f"Generating OpenAI TTS for text: '{text[:30]}...'")
            
            # Using 'alloy' or 'shimmer' or 'nova' or 'fable' - 'shimmer' or 'alloy' is nice for kids
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )
            response.write_to_file(output_path)
            logger.info(f"OpenAI TTS saved to: {output_path}")
            return os.path.abspath(output_path)
        except Exception as e:
            logger.error(f"OpenAI TTS failed ({e}). Falling back to gTTS.")

    # Default to gTTS (Google Text-to-Speech)
    try:
        from gtts import gTTS
        logger.info(f"Generating gTTS for text: '{text[:30]}...'")
        
        # 'en' with tld 'com' gives standard US accent
        tts = gTTS(text=text, lang="en", tld="com", slow=False)
        tts.save(output_path)
        logger.info(f"gTTS saved to: {output_path}")
        return os.path.abspath(output_path)
    except Exception as e:
        logger.warning(f"gTTS failed: {e}. Generating offline synthetic fallback voiceover...")
        try:
            return generate_offline_synthetic_audio(text, output_path)
        except Exception as fallback_err:
            logger.error(f"Offline synthetic TTS fallback failed: {fallback_err}")
            raise RuntimeError(f"Failed to generate TTS with any provider. error: {e}")

def generate_offline_synthetic_audio(text: str, output_path: str) -> str:
    """
    Generates a soft, modulated 16-bit PCM WAV audio file simulating a voice hum
    for fully offline testing and dry-runs.
    """
    import wave
    import struct
    import math

    # Estimate duration: kids content is slow-paced (about 10 characters per second)
    duration = max(2.5, len(text) / 10.0)
    sample_rate = 22050
    num_samples = int(sample_rate * duration)
    
    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = i / sample_rate
            # 2Hz modulation for word spacing simulation
            envelope = 0.4 + 0.4 * math.sin(2 * math.pi * 2.0 * t)
            # Soft low frequency pitch (200Hz) with some intonation waviness
            freq = 200.0 + 25.0 * math.sin(2 * math.pi * 0.4 * t)
            
            val = math.sin(2 * math.pi * freq * t) * envelope * 10000
            data = struct.pack('<h', int(val))
            wav_file.writeframesraw(data)
            
    logger.info(f"Offline synthetic voiceover generated (duration={duration:.2f}s): {output_path}")
    return os.path.abspath(output_path)
