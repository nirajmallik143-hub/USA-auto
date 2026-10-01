import os
import unittest
from PIL import Image
from src.ai_generation import generate_kids_script
from src.tts import generate_voiceover
from src.asset_manager import generate_procedural_background
from src.video_renderer import wrap_text

class TestKidsPipeline(unittest.TestCase):
    
    def test_ai_generation_structure(self):
        """Test that the AI generator returns proper schema."""
        script = generate_kids_script("learning", is_short=True)
        self.assertIn("title", script)
        self.assertIn("category", script)
        self.assertIn("scenes", script)
        self.assertGreater(len(script["scenes"]), 0)
        for scene in script["scenes"]:
            self.assertIn("title", scene)
            self.assertIn("text", scene)

    def test_procedural_background_generation(self):
        """Test that the procedural background generator creates images of correct size."""
        size = (100, 100)
        bg_path = generate_procedural_background(size, theme_index=1)
        self.assertTrue(os.path.exists(bg_path))
        
        # Verify the dimensions of the generated image
        with Image.open(bg_path) as img:
            self.assertEqual(img.size, size)
            
        # Clean up
        if os.path.exists(bg_path):
            os.remove(bg_path)

    def test_tts_generation(self):
        """Test gTTS voiceover file generation."""
        output_path = "/tmp/test_voiceover.mp3"
        if os.path.exists(output_path):
            os.remove(output_path)
            
        # Small speech text
        path = generate_voiceover("Hello little friends!", output_path, provider="gtts")
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.abspath(output_path), path)
        
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
