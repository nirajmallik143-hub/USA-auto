import os
import random
import logging
import requests
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

# Warm, engaging kids-friendly color palettes (primary background, shapes/decorations)
KIDS_PALETTES = [
    {"bg": (173, 216, 230), "shapes": [(255, 182, 193), (255, 255, 224), (144, 238, 144)]}, # Pastel Sky, Pink, Yellow, Green
    {"bg": (255, 228, 225), "shapes": [(255, 218, 185), (230, 230, 250), (176, 224, 230)]}, # Misty Rose, Peach, Lavender, Powder Blue
    {"bg": (240, 255, 240), "shapes": [(255, 239, 213), (255, 240, 245), (152, 251, 152)]}, # Honeydew, Papaya, Lavender Blush, Pale Green
    {"bg": (253, 245, 230), "shapes": [(255, 222, 173), (224, 255, 255), (255, 192, 203)]}, # Old Lace, Navajo White, Light Cyan, Pink
    {"bg": (230, 242, 255), "shapes": [(255, 204, 204), (204, 255, 204), (255, 255, 204)]}  # Light Blue, Soft Red, Soft Green, Soft Yellow
]

def search_pexels_videos(query: str, orientation: str = "portrait") -> Optional[str]:
    """
    Searches for a stock video on Pexels and returns the video download URL.
    orientation: 'portrait' (9:16) or 'landscape' (16:9)
    """
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        logger.info("No Pexels API key found in environment.")
        return None

    headers = {"Authorization": api_key}
    url = "https://api.pexels.com/videos/search"
    params = {
        "query": query,
        "orientation": orientation,
        "per_page": 5,
        "size": "medium"
    }

    try:
        logger.info(f"Searching Pexels for videos with query: '{query}' ({orientation})")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            if videos:
                # Select a random video from top results for variety
                video = random.choice(videos)
                video_files = video.get("video_files", [])
                
                # Try to find a link with HD quality
                hd_files = [vf for vf in video_files if vf.get("quality") == "hd" or "1080" in str(vf.get("height", ""))]
                if hd_files:
                    download_url = hd_files[0].get("link")
                    logger.info(f"Found HD video file: {download_url}")
                    return download_url
                elif video_files:
                    download_url = video_files[0].get("link")
                    logger.info(f"Found fallback video file: {download_url}")
                    return download_url
        else:
            logger.warning(f"Pexels search API returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to search Pexels: {e}")
    return None


def download_file(url: str, output_path: str) -> bool:
    """Downloads a file from a URL and saves it to output_path."""
    try:
        logger.info(f"Downloading asset from: {url}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Successfully downloaded to: {output_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to download file from {url}: {e}")
    return False


def generate_procedural_background(size: Tuple[int, int], theme_index: int) -> str:
    """
    Generates a beautiful kid-friendly procedurally generated background image with
    playful elements (circles, bubbles, clouds, stars) using Pillow and saves it to a file.
    Returns:
        str: Absolute path to the generated image file.
    """
    width, height = size
    # Create background image
    palette = KIDS_PALETTES[theme_index % len(KIDS_PALETTES)]
    img = Image.new("RGB", size, palette["bg"])
    draw = ImageDraw.Draw(img)

    # Draw fun circles/bubbles
    num_shapes = random.randint(12, 20)
    for _ in range(num_shapes):
        shape_color = random.choice(palette["shapes"])
        # Give shapes transparency/softness by blending
        radius = random.randint(min(width, height) // 15, min(width, height) // 5)
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        
        # Create an overlay layer for transparent drawing
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Random shape: circle, rounded rectangle, or star-like polygon
        shape_type = random.choice(["circle", "circle", "rect"])
        alpha = random.randint(40, 100) # Semi-transparent
        color_with_alpha = shape_color + (alpha,)
        
        if shape_type == "circle":
            overlay_draw.ellipse(
                [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                fill=color_with_alpha
            )
        elif shape_type == "rect":
            rw = radius * 1.5
            rh = radius * 1.2
            overlay_draw.rounded_rectangle(
                [(cx - rw, cy - rh), (cx + rw, cy + rh)],
                radius=radius // 4,
                fill=color_with_alpha
            )
            
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Add a soft vignette or frame border
    # We can do this with a subtle gradient overlay
    border_color = (255, 255, 255, 25)
    border_width = min(width, height) // 40
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(border_width, border_width), (width - border_width, height - border_width)],
        outline=border_color,
        width=border_width
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    output_dir = "assets/backgrounds"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"bg_{theme_index}_{width}x{height}.png")
    img.save(output_path, "PNG")
    logger.info(f"Generated procedural background saved to: {output_path}")
    return os.path.abspath(output_path)


def get_background_music() -> Optional[str]:
    """
    Finds or downloads an upbeat kid-friendly instrumental music track.
    Downloads a royalty-free track from an archive or open-source site,
    or falls back to generating a synthesized soft offline backing track.
    """
    music_url_kids = "https://pub-c5e31b5cdafb419a86617dd3e911240c.r2.dev/happy-ukulele.mp3"
    music_url_mp3 = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

    output_dir = "assets/music"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "happy_kids_background.mp3")
    synth_path = os.path.join(output_dir, "happy_kids_background_synth.wav")
    
    if os.path.exists(output_path):
        return os.path.abspath(output_path)
    if os.path.exists(synth_path):
        return os.path.abspath(synth_path)

    # Attempt to download the track
    success = download_file(music_url_kids, output_path)
    if success:
        return os.path.abspath(output_path)
        
    # Second attempt fallback
    success = download_file(music_url_mp3, output_path)
    if success:
        return os.path.abspath(output_path)

    # Offline synthetic music fallback
    logger.warning("Background music download failed. Synthesizing a cute, soft offline backing track...")
    try:
        return generate_offline_background_music(synth_path)
    except Exception as e:
        logger.error(f"Failed to generate offline background music: {e}")
        return None


def generate_offline_background_music(output_path: str) -> str:
    """
    Synthesizes a 15-second upbeat, soft, lullaby-like chord progression
    (C Major -> F Major -> G Major -> C Major) using math waves.
    Saves as a WAV file.
    """
    import wave
    import struct
    import math

    sample_rate = 22050
    duration = 16.0  # 4 bars of 4 seconds each
    num_samples = int(sample_rate * duration)

    # Frequency mappings
    freqs = {
        "C4": 261.63, "E4": 329.63, "G4": 392.00,
        "F4": 349.23, "A4": 440.00, "C5": 523.25,
        "B4": 493.88, "D5": 587.33
    }

    # Playful chord progression (C -> F -> G -> C)
    progression = [
        ["C4", "E4", "G4"], # C Major
        ["F4", "A4", "C5"], # F Major
        ["G4", "B4", "D5"], # G Major
        ["C4", "E4", "G4"]  # C Major
    ]

    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            bar = int((t % 16) / 4)  # 0 to 3
            chord = progression[bar]
            
            # Draw individual notes with gentle decay on beat (1 beat per second)
            beat_t = t % 1.0
            decay = math.exp(-3.0 * beat_t)  # Fast decay for a clean plucked feel
            
            val = 0.0
            for note in chord:
                freq = freqs[note]
                # Combine a fundamental sine wave with a subtle bright overtone (plucked instrument feel)
                val += math.sin(2 * math.pi * freq * t) * decay
                val += 0.3 * math.sin(2 * math.pi * freq * 2.0 * t) * decay * 0.5

            # Master mix volume compression (keep it soft)
            mixed_val = (val / len(chord)) * 4000
            data = struct.pack("<h", int(mixed_val))
            wav_file.writeframesraw(data)

    logger.info(f"Synthesized offline background music: {output_path}")
    return os.path.abspath(output_path)
