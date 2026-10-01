"""
Auto-caption and subtitle overlay generator for kids videos.
Generates high-contrast, rounded subtitle badge overlays with safe margins for 9:16 Shorts and 16:9 Long.
"""

from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

from src.config import VideoFormat
from src.logger import logger


class SubtitleGenerator:
    """Generates kid-friendly animated/styled subtitle overlays."""

    def __init__(self):
        pass

    def create_caption_overlay(
        self,
        text: str,
        video_format: str,
        output_path: Path,
    ) -> Path:
        """
        Render an RGBA transparent overlay with high-contrast, kid-friendly captions.
        Avoids ImageMagick dependency by using Pillow directly.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if video_format == VideoFormat.SHORTS.value:
            width, height = 1080, 1920
            # Shorts safe zone: middle-lower (60% to 75% down)
            center_y = int(height * 0.68)
            max_badge_w = int(width * 0.88)
        else:
            width, height = 1920, 1080
            # Long-form safe zone: bottom-third (80% down)
            center_y = int(height * 0.82)
            max_badge_w = int(width * 0.75)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Word wrap text cleanly
        words = text.strip().split()
        lines: List[str] = []
        current_line: List[str] = []

        # Target 3-5 words per line for quick kid readability
        max_words_per_line = 4 if video_format == VideoFormat.SHORTS.value else 7
        for word in words:
            current_line.append(word)
            if len(current_line) >= max_words_per_line:
                lines.append(" ".join(current_line))
                current_line = []
        if current_line:
            lines.append(" ".join(current_line))

        # Font configuration
        font_size = 54 if video_format == VideoFormat.SHORTS.value else 48
        try:
            # Look for common clean TTF fonts if present, else fallback
            font = None
            for font_name in ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial.ttf"]:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Calculate bounding dimensions
        line_height = int(font_size * 1.3)
        total_text_h = len(lines) * line_height
        badge_padding_x = 40
        badge_padding_y = 25

        badge_h = total_text_h + badge_padding_y * 2
        badge_w = min(max_badge_w, max(len(l) * int(font_size * 0.55) + badge_padding_x * 2 for l in lines))

        badge_x1 = (width - badge_w) // 2
        badge_y1 = center_y - badge_h // 2
        badge_x2 = badge_x1 + badge_w
        badge_y2 = badge_y1 + badge_h

        # Draw semi-transparent rounded dark pill badge background (for maximum legibility)
        badge_bg = (20, 20, 30, 220)  # Deep navy/black with high alpha
        badge_border = (255, 235, 59, 255)  # Bright cheerful yellow border
        draw.rounded_rectangle(
            [badge_x1, badge_y1, badge_x2, badge_y2],
            radius=20,
            fill=badge_bg,
            outline=badge_border,
            width=5,
        )

        # Draw each line of text with bright high-contrast color
        curr_y = badge_y1 + badge_padding_y
        for line in lines:
            # Simple horizontal centering
            line_w = len(line) * int(font_size * 0.5)
            text_x = (width - line_w) // 2

            # Drop shadow
            draw.text((text_x + 3, curr_y + 3), line, font=font, fill=(0, 0, 0, 255))
            # Text fill (Bright White / Canary Yellow)
            draw.text((text_x, curr_y), line, font=font, fill=(255, 255, 255, 255))
            curr_y += line_height

        overlay.save(str(output_path), format="PNG")
        return output_path


subtitle_generator = SubtitleGenerator()
