import os
import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip,
    ImageClip,
    VideoFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    CompositeAudioClip
)
from moviepy.video.fx import Loop, Resize
from moviepy.audio.fx import AudioLoop
from src.tts import generate_voiceover
from src.asset_manager import (
    search_pexels_videos,
    download_file,
    generate_procedural_background,
    get_background_music
)

logger = logging.getLogger(__name__)

# Standard Bold Kids-friendly Font
DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps text into multiple lines fitting within max_width."""
    words = text.split()
    if not words:
        return []
    
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        except AttributeError:
            w, _ = draw.textsize(test_line, font=font)
            
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    text: str,
    position: Tuple[int, int],
    font: ImageFont.ImageFont,
    text_color: Tuple[int, int, int],
    stroke_color: Tuple[int, int, int],
    stroke_width: int,
    max_width: int,
    align: str = "center"
) -> int:
    """
    Draws text wrapped to fit max_width with an outline.
    Returns the total height of the rendered block.
    """
    lines = wrap_text(text, font, max_width, draw)
    current_y = position[1]
    
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(line, font=font)
            
        if align == "center":
            x = position[0] - (w // 2)
        else:
            x = position[0]
            
        draw.text(
            (x, current_y),
            line,
            font=font,
            fill=text_color,
            stroke_fill=stroke_color,
            stroke_width=stroke_width
        )
        current_y += h + int(h * 0.3) # Line height spacing
        
    return current_y - position[1]


def create_static_scene_frame(
    bg_image_path: str,
    size: Tuple[int, int],
    title: str,
    subtitle_text: str,
    font_path: str = DEFAULT_FONT_PATH
) -> Image.Image:
    """
    Composites background, title, and wrapped subtitles into a single PIL Image.
    """
    width, height = size
    bg_img = Image.open(bg_image_path).resize(size, Image.Resampling.LANCZOS)
    
    # Create overlay
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Load fonts
    try:
        title_font = ImageFont.truetype(font_path, int(width * 0.055))
        subtitle_font = ImageFont.truetype(font_path, int(width * 0.045))
    except Exception:
        logger.warning(f"Could not load font {font_path}, falling back to default.")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        
    # Draw scene title at top
    title_pos = (width // 2, int(height * 0.12))
    max_title_width = int(width * 0.85)
    draw_text_with_outline(
        draw,
        title,
        title_pos,
        title_font,
        text_color=(255, 255, 102), # Bright Kids Yellow
        stroke_color=(20, 20, 20),
        stroke_width=int(width * 0.007),
        max_width=max_title_width,
        align="center"
    )
    
    # Draw spoken text/subtitle at bottom
    sub_pos = (width // 2, int(height * 0.70))
    max_sub_width = int(width * 0.85)
    
    # To make text even more legible, we can draw a translucent backing box
    # First wrap text to know the bounding box height
    dummy_img = Image.new("RGBA", (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)
    sub_lines = wrap_text(subtitle_text, subtitle_font, max_sub_width, dummy_draw)
    
    try:
        char_bbox = dummy_draw.textbbox((0, 0), "A", font=subtitle_font)
        char_h = char_bbox[3] - char_bbox[1]
    except AttributeError:
        _, char_h = dummy_draw.textsize("A", font=subtitle_font)
        
    total_sub_h = len(sub_lines) * (char_h + int(char_h * 0.3))
    
    # Semi-transparent backing rectangle
    padding = 20
    box_y1 = sub_pos[1] - padding
    box_y2 = sub_pos[1] + total_sub_h + padding
    draw.rounded_rectangle(
        [(width // 2 - max_sub_width // 2 - padding, box_y1), (width // 2 + max_sub_width // 2 + padding, box_y2)],
        radius=15,
        fill=(0, 0, 0, 90) # Black with ~35% opacity
    )
    
    # Draw subtitles inside the backing box
    draw_text_with_outline(
        draw,
        subtitle_text,
        sub_pos,
        subtitle_font,
        text_color=(255, 255, 255), # Clean White
        stroke_color=(0, 0, 0),
        stroke_width=int(width * 0.006),
        max_width=max_sub_width,
        align="center"
    )
    
    # Composite layers
    final_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay)
    return final_img.convert("RGB")


def create_text_overlay_clip(
    size: Tuple[int, int],
    title: str,
    subtitle_text: str,
    duration: float,
    font_path: str = DEFAULT_FONT_PATH
) -> CompositeVideoClip:
    """
    Creates a transparent video overlay clip of title and subtitle.
    Used for overlaying text onto stock background video footage.
    """
    width, height = size
    # Generate transparent image
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    try:
        title_font = ImageFont.truetype(font_path, int(width * 0.055))
        subtitle_font = ImageFont.truetype(font_path, int(width * 0.045))
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        
    # Draw scene title
    title_pos = (width // 2, int(height * 0.12))
    max_title_width = int(width * 0.85)
    draw_text_with_outline(
        draw,
        title,
        title_pos,
        title_font,
        text_color=(255, 255, 102),
        stroke_color=(20, 20, 20),
        stroke_width=int(width * 0.007),
        max_width=max_title_width,
        align="center"
    )
    
    # Draw subtitles
    sub_pos = (width // 2, int(height * 0.70))
    max_sub_width = int(width * 0.85)
    
    # Draw soft backing rectangle
    dummy_img = Image.new("RGBA", (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)
    sub_lines = wrap_text(subtitle_text, subtitle_font, max_sub_width, dummy_draw)
    try:
        char_bbox = dummy_draw.textbbox((0, 0), "A", font=subtitle_font)
        char_h = char_bbox[3] - char_bbox[1]
    except AttributeError:
        _, char_h = dummy_draw.textsize("A", font=subtitle_font)
    total_sub_h = len(sub_lines) * (char_h + int(char_h * 0.3))
    
    padding = 20
    box_y1 = sub_pos[1] - padding
    box_y2 = sub_pos[1] + total_sub_h + padding
    draw.rounded_rectangle(
        [(width // 2 - max_sub_width // 2 - padding, box_y1), (width // 2 + max_sub_width // 2 + padding, box_y2)],
        radius=15,
        fill=(0, 0, 0, 90)
    )
    
    draw_text_with_outline(
        draw,
        subtitle_text,
        sub_pos,
        subtitle_font,
        text_color=(255, 255, 255),
        stroke_color=(0, 0, 0),
        stroke_width=int(width * 0.006),
        max_width=max_sub_width,
        align="center"
    )
    
    rgba_array = np.array(overlay)
    rgb_array = rgba_array[:, :, :3]
    alpha_array = rgba_array[:, :, 3] / 255.0
    
    # Construct transparent MoviePy clip
    mask_clip = ImageClip(alpha_array, ismask=True).set_duration(duration)
    text_clip = ImageClip(rgb_array).set_mask(mask_clip).set_duration(duration)
    return text_clip


def render_video_pipeline(
    script: Dict[str, Any],
    is_short: bool = True,
    output_filename: str = None
) -> str:
    """
    Generates and composites TTS audio, kids' themed backgrounds, and bold styled subtitles
    into a finished HD MP4 video file.
    """
    category = script.get("category", "learning")
    title = script.get("title", "Kids Video")
    scenes = script.get("scenes", [])
    
    # Output file settings
    output_dir = os.getenv("OUTPUT_DIR", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    if not output_filename:
        safe_title = "".join([c if c.isalnum() else "_" for c in title.replace(" ", "_")])
        suffix = "short" if is_short else "long"
        output_filename = f"{safe_title}_{suffix}.mp4"
        
    output_path = os.path.join(output_dir, output_filename)
    
    # 9:16 for Shorts, 16:9 for long videos
    size = (1080, 1920) if is_short else (1920, 1080)
    orientation = "portrait" if is_short else "landscape"
    
    scene_clips = []
    temp_files = []
    
    logger.info(f"Starting rendering pipeline for '{title}' (Shorts={is_short})")
    
    try:
        for idx, scene in enumerate(scenes):
            scene_title = scene.get("title", f"Scene {idx+1}")
            scene_text = scene.get("text", "")
            
            # 1. Generate Voiceover MP3
            voiceover_path = f"/tmp/scene_{idx}_voiceover.mp3"
            generate_voiceover(scene_text, voiceover_path)
            temp_files.append(voiceover_path)
            
            # Load voiceover to measure duration
            audio_clip = AudioFileClip(voiceover_path)
            duration = audio_clip.duration
            
            # 2. Get Background Asset
            # We try to search Pexels first
            video_url = search_pexels_videos(scene_title, orientation=orientation)
            bg_video_path = f"/tmp/scene_{idx}_bg.mp4" if video_url else None
            
            bg_clip = None
            if video_url and download_file(video_url, bg_video_path):
                temp_files.append(bg_video_path)
                try:
                    video_clip = VideoFileClip(bg_video_path)
                    # Resize/crop to fill screen properly using modern MoviePy v2 effects
                    if is_short:
                        video_clip = video_clip.with_effects([Resize(height=size[1])])
                    else:
                        video_clip = video_clip.with_effects([Resize(width=size[0])])
                    
                    # Loop or clip video to match audio duration
                    if video_clip.duration < duration:
                        bg_clip = video_clip.with_effects([Loop(duration=duration)])
                    else:
                        bg_clip = video_clip.subclipped(0, duration)
                        
                    # Mute source audio in stock video
                    bg_clip = bg_clip.without_audio()
                except Exception as e:
                    logger.warning(f"Failed to use Pexels video clip ({e}). Falling back to procedural.")
                    bg_clip = None
            
            # If no stock video, generate a beautiful procedural background
            if bg_clip is None:
                bg_image_path = generate_procedural_background(size, theme_index=idx)
                # Render fully static frame directly in PIL to optimize performance and prevent compositing overhead
                final_scene_img = create_static_scene_frame(bg_image_path, size, scene_title, scene_text)
                
                # Convert PIL image to numpy array
                scene_frame_array = np.array(final_scene_img)
                bg_clip = ImageClip(scene_frame_array).with_duration(duration)
                
                # The visual has text baked in, so no extra text overlay is needed!
                scene_clip = bg_clip.with_audio(audio_clip)
            else:
                # If we used a Pexels video, we must overlay the text on top
                text_overlay = create_text_overlay_clip(size, scene_title, scene_text, duration)
                composite_clip = CompositeVideoClip([bg_clip, text_overlay], size=size)
                scene_clip = composite_clip.with_audio(audio_clip)
                
            scene_clips.append(scene_clip)
            
        # 3. Concatenate all scenes into one continuous video
        logger.info(f"Concatenating {len(scene_clips)} scene clips...")
        final_video = concatenate_videoclips(scene_clips, method="compose")
        total_duration = final_video.duration
        
        # 4. Process and Mix Background Music
        music_path = get_background_music()
        if music_path:
            try:
                music_clip = AudioFileClip(music_path)
                # Loop background music if it is too short
                if music_clip.duration < total_duration:
                    music_clip = music_clip.with_effects([AudioLoop(duration=total_duration)])
                else:
                    music_clip = music_clip.subclipped(0, total_duration)
                    
                # Lower the volume of background music to avoid overriding voiceover (12% volume is safe)
                music_clip = music_clip.with_volume_scaled(0.12)
                
                # Combine voiceovers and background music
                mixed_audio = CompositeAudioClip([final_video.audio, music_clip])
                final_video = final_video.with_audio(mixed_audio)
                logger.info("Successfully layered kid-friendly background music.")
            except Exception as e:
                logger.error(f"Failed to apply background music track: {e}")
                
        # 5. Render final output video using multi-threading
        logger.info(f"Rendering final MP4 to {output_path}...")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium",
            logger="bar" # MoviePy console progress bar
        )
        logger.info(f"Successfully generated final video: {output_path}")
        
    finally:
        # Clean up resource descriptors
        for clip in scene_clips:
            try:
                clip.close()
            except Exception:
                pass
        try:
            final_video.close()
        except Exception:
            pass
            
        # Clean up temporary visual and audio files in /tmp to keep environment tidy
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_file}: {e}")
                    
    return os.path.abspath(output_path)
