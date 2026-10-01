"""
Automated visual asset selector and procedural kid-friendly background generator.
Fetches stock media (Pexels / Pixabay) or procedurally generates vibrant, high-res kid backgrounds.
"""

import math
import random
from pathlib import Path
from typing import Any, List, Optional, Tuple
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.config import VideoFormat, VideoTopic, settings
from src.content.topics import get_topic_definition
from src.logger import logger


class ProceduralKidBackgroundGenerator:
    """Generates vibrant, playful backgrounds tailored for US kids content."""

    def __init__(self):
        pass

    def get_resolution(self, video_format: str) -> Tuple[int, int]:
        """Return (width, height) based on format."""
        if video_format == VideoFormat.SHORTS.value:
            return (1080, 1920)  # 9:16 vertical
        return (1920, 1080)      # 16:9 horizontal

    def generate_scene_image(
        self,
        video_format: str,
        topic: str,
        scene_index: int,
        scene_text: str,
        output_path: Path,
    ) -> Path:
        """Create a colorful, kid-friendly background slide for a given scene."""
        width, height = self.get_resolution(video_format)
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw base themed gradient
        self._draw_theme_gradient(draw, width, height, topic, scene_index)

        # Draw thematic decorative elements
        if topic == VideoTopic.SPACE_FACTS.value:
            self._draw_space_elements(draw, width, height, scene_index)
        elif topic == VideoTopic.ANIMAL_RIDDLES.value or topic == VideoTopic.DINOSAUR_ADVENTURES.value:
            self._draw_nature_elements(draw, width, height, scene_index)
        elif topic == VideoTopic.MORAL_STORIES.value:
            self._draw_fairytale_elements(draw, width, height, scene_index)
        elif topic == VideoTopic.KIDS_JOKES_PUZZLES.value:
            self._draw_carnival_elements(draw, width, height, scene_index)
        else:
            self._draw_classroom_elements(draw, width, height, scene_index)

        # Draw central decorative theme badge/frame
        self._draw_theme_badge(draw, width, height, topic, scene_index, video_format)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")
        return output_path

    def _draw_theme_gradient(
        self, draw: ImageDraw.ImageDraw, width: int, height: int, topic: str, scene_idx: int
    ) -> None:
        """Draw smooth vertical color gradient with kid-friendly color palettes."""
        palettes = {
            VideoTopic.SPACE_FACTS.value: [(15, 12, 41), (48, 43, 99), (36, 36, 62)],
            VideoTopic.ANIMAL_RIDDLES.value: [(255, 179, 71), (255, 204, 51), (102, 187, 106)],
            VideoTopic.MORAL_STORIES.value: [(255, 154, 139), (255, 106, 136), (155, 89, 182)],
            VideoTopic.KIDS_JOKES_PUZZLES.value: [(255, 110, 127), (191, 233, 255), (107, 185, 240)],
            VideoTopic.SCIENCE_CURIOSITIES.value: [(0, 198, 255), (0, 114, 255), (142, 68, 173)],
            VideoTopic.ALPHABET_NUMBER_LEARNING.value: [(255, 238, 173), (255, 111, 105), (150, 206, 180)],
            VideoTopic.DINOSAUR_ADVENTURES.value: [(56, 142, 60), (139, 195, 74), (255, 193, 7)],
        }
        colors = palettes.get(topic, [(66, 165, 245), (144, 202, 249), (255, 235, 59)])
        c1, c2, c3 = colors

        # Interpolate 3-stop vertical gradient
        for y in range(height):
            ratio = y / float(height)
            if ratio < 0.5:
                sub_ratio = ratio * 2.0
                r = int(c1[0] + (c2[0] - c1[0]) * sub_ratio)
                g = int(c1[1] + (c2[1] - c1[1]) * sub_ratio)
                b = int(c1[2] + (c2[2] - c1[2]) * sub_ratio)
            else:
                sub_ratio = (ratio - 0.5) * 2.0
                r = int(c2[0] + (c3[0] - c2[0]) * sub_ratio)
                g = int(c2[1] + (c3[1] - c2[1]) * sub_ratio)
                b = int(c2[2] + (c3[2] - c2[2]) * sub_ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    def _draw_space_elements(self, draw: ImageDraw.ImageDraw, width: int, height: int, seed: int) -> None:
        rng = random.Random(seed * 42 + 7)
        # Twinkling stars
        for _ in range(80):
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            radius = rng.randint(2, 6)
            star_color = rng.choice([(255, 255, 255), (255, 235, 59), (129, 212, 250)])
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=star_color)

        # Cartoon Moon or Planet
        cx, cy = width * 0.8, height * 0.18
        r = min(width, height) * 0.12
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 213, 79))
        draw.ellipse([cx - r * 0.6, cy - r * 0.8, cx + r * 0.8, cy + r * 0.6], fill=(255, 179, 0, 100))

    def _draw_nature_elements(self, draw: ImageDraw.ImageDraw, width: int, height: int, seed: int) -> None:
        rng = random.Random(seed * 23 + 11)
        # Rolling green hills at bottom
        hill_color = (67, 160, 71)
        draw.chord([0, int(height * 0.65), width, int(height * 1.3)], 0, 180, fill=hill_color)
        draw.chord([int(width * 0.3), int(height * 0.72), int(width * 1.5), int(height * 1.4)], 0, 180, fill=(46, 125, 50))

        # Floating smiling sun
        sx, sy = int(width * 0.18), int(height * 0.15)
        sr = int(min(width, height) * 0.1)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 238, 88))
        # Sun rays
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x1 = sx + int((sr + 5) * math.cos(rad))
            y1 = sy + int((sr + 5) * math.sin(rad))
            x2 = sx + int((sr + 25) * math.cos(rad))
            y2 = sy + int((sr + 25) * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=(255, 214, 0), width=4)

    def _draw_fairytale_elements(self, draw: ImageDraw.ImageDraw, width: int, height: int, seed: int) -> None:
        rng = random.Random(seed * 31 + 5)
        # Floating magical golden sparkle particles
        for _ in range(60):
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            radius = rng.randint(3, 8)
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(255, 245, 157))

    def _draw_carnival_elements(self, draw: ImageDraw.ImageDraw, width: int, height: int, seed: int) -> None:
        rng = random.Random(seed * 19 + 3)
        colors = [(255, 64, 129), (255, 235, 59), (76, 175, 80), (33, 150, 243), (156, 39, 176)]
        # Confetti pieces
        for _ in range(70):
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            w = rng.randint(8, 20)
            h = rng.randint(8, 20)
            draw.rectangle([x, y, x + w, y + h], fill=rng.choice(colors))

    def _draw_classroom_elements(self, draw: ImageDraw.ImageDraw, width: int, height: int, seed: int) -> None:
        rng = random.Random(seed * 17 + 9)
        # Colorful floating bubbles / geometric circles
        colors = [(255, 205, 210), (187, 222, 251), (200, 230, 201), (255, 249, 196)]
        for _ in range(35):
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            r = rng.randint(20, 60)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=rng.choice(colors))

    def _draw_theme_badge(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        topic: str,
        scene_idx: int,
        video_format: str,
    ) -> None:
        """Draw a rounded kid-friendly decorative banner card."""
        topic_def = get_topic_definition(topic)
        # Banner dimensions
        card_w = int(width * 0.85) if video_format == VideoFormat.SHORTS.value else int(width * 0.6)
        card_h = int(height * 0.22) if video_format == VideoFormat.SHORTS.value else int(height * 0.26)
        cx = width // 2
        cy = int(height * 0.38) if video_format == VideoFormat.SHORTS.value else int(height * 0.42)

        x1 = cx - card_w // 2
        y1 = cy - card_h // 2
        x2 = cx + card_w // 2
        y2 = cy + card_h // 2

        # Card shadow
        draw.rounded_rectangle([x1 + 6, y1 + 6, x2 + 6, y2 + 6], radius=24, fill=(0, 0, 0, 60))
        # White glossy card background
        draw.rounded_rectangle([x1, y1, x2, y2], radius=24, fill=(255, 255, 255), outline=(255, 214, 0), width=6)

        # Text inside card
        header_text = f"⭐ {topic_def.name.upper()} ⭐"
        step_text = f"Scene #{scene_idx + 1}"

        # Draw clean indicator lines
        try:
            # Try default PIL font or fallback
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
        except Exception:
            font_title = None
            font_sub = None

        # Center label
        draw.text((cx - len(header_text) * 3, y1 + 25), header_text, fill=(216, 27, 96))
        draw.text((cx - len(step_text) * 3, y2 - 40), step_text, fill=(30, 136, 229))


class VisualAssetManager:
    """Manages visual assets, selecting stock footage/images or procedural graphics."""

    def __init__(self):
        self.procedural = ProceduralKidBackgroundGenerator()

    def generate_scene_visuals(
        self,
        video_format: str,
        topic: str,
        scenes: List[Any],
        job_temp_dir: Path,
    ) -> List[Path]:
        """
        Generate or fetch visual background files for each scene.
        Returns list of image paths for the scenes.
        """
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        visual_paths = []

        for i, scene in enumerate(scenes):
            scene_img_path = job_temp_dir / f"scene_{i:02d}_visual.png"
            # Check if stock asset can be downloaded
            stock_fetched = False
            if settings.pexels_api_key or settings.pixabay_api_key:
                stock_fetched = self._try_fetch_stock(scene.visual_description, scene_img_path)

            if not stock_fetched:
                # Use procedural generator
                self.procedural.generate_scene_image(
                    video_format=video_format,
                    topic=topic,
                    scene_index=i,
                    scene_text=scene.caption_text,
                    output_path=scene_img_path,
                )

            visual_paths.append(scene_img_path)

        logger.info(f"Generated {len(visual_paths)} visual assets for {video_format} job in {job_temp_dir.name}")
        return visual_paths

    def _try_fetch_stock(self, query: str, output_path: Path) -> bool:
        """Fetch stock image from Pexels API if key is available."""
        if not settings.pexels_api_key:
            return False
        try:
            headers = {"Authorization": settings.pexels_api_key}
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("photos"):
                    img_url = data["photos"][0]["src"]["large2x"]
                    img_data = requests.get(img_url, timeout=15).content
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    return True
        except Exception as e:
            logger.warning(f"Failed to fetch stock asset for '{query}': {e}")
        return False


visual_manager = VisualAssetManager()
