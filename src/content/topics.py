"""
Topics and educational themes targeted at US kids (ages 3–8).
Includes metadata, keywords, learning goals, and visual aesthetic guidelines.
"""

from dataclasses import dataclass
from typing import Dict, List
from src.config import VideoTopic


@dataclass
class TopicDefinition:
    id: str
    name: str
    target_age: str
    description: str
    educational_goal: str
    keywords: List[str]
    color_palette: List[str]  # Hex or RGB names for vibrant kid visual themes
    bg_style: str  # e.g., "nature", "space", "cartoon_room", "chalkboard"


TOPIC_CATALOG: Dict[str, TopicDefinition] = {
    VideoTopic.ANIMAL_RIDDLES.value: TopicDefinition(
        id=VideoTopic.ANIMAL_RIDDLES.value,
        name="Animal Riddles & Mystery Creatures",
        target_age="3-7",
        description="Interactive guess-the-animal riddles with animal sounds and cheerful hints.",
        educational_goal="Enhance deduction, vocabulary, and zoological curiosity.",
        keywords=["cute animal", "lion", "elephant", "puppy", "dolphin", "cartoon animal", "wildlife for kids"],
        color_palette=["#4CAF50", "#FFEB3B", "#FF9800", "#8BC34A"],
        bg_style="nature_savannah",
    ),
    VideoTopic.MORAL_STORIES.value: TopicDefinition(
        id=VideoTopic.MORAL_STORIES.value,
        name="Heartwarming Moral Stories",
        target_age="4-8",
        description="Gentle, uplifting fables teaching honesty, kindness, sharing, and perseverance.",
        educational_goal="Foster emotional intelligence, social empathy, and moral growth.",
        keywords=["friendly forest", "kindness story", "sharing toys", "friendship fable", "cute cartoon character"],
        color_palette=["#FF7043", "#FFA726", "#FFCA28", "#81C784"],
        bg_style="fairy_tale_forest",
    ),
    VideoTopic.ALPHABET_NUMBER_LEARNING.value: TopicDefinition(
        id=VideoTopic.ALPHABET_NUMBER_LEARNING.value,
        name="Super ABC & 123 Counting Adventures",
        target_age="3-6",
        description="Engaging phonics, letters, numbers 1-10, shapes, and colorful object counting.",
        educational_goal="Early childhood literacy, phonetic awareness, and early numeracy.",
        keywords=["alphabet letters", "counting numbers", "colorful toys", "shapes for kids", "bright cartoon classroom"],
        color_palette=["#E91E63", "#9C27B0", "#03A9F4", "#FFEB3B"],
        bg_style="colorful_classroom",
    ),
    VideoTopic.SPACE_FACTS.value: TopicDefinition(
        id=VideoTopic.SPACE_FACTS.value,
        name="Cosmic Space Explorer",
        target_age="4-8",
        description="Fun, mind-blowing facts about the Moon, Solar System planets, astronauts, and glittering stars.",
        educational_goal="Inspire wonder in astronomy, exploration, and scientific discovery.",
        keywords=["space galaxy", "solar system", "astronaut kid", "planet saturn", "cartoon rocket ship"],
        color_palette=["#1A237E", "#311B92", "#00BCD4", "#FFD54F"],
        bg_style="deep_space_stars",
    ),
    VideoTopic.DINOSAUR_ADVENTURES.value: TopicDefinition(
        id=VideoTopic.DINOSAUR_ADVENTURES.value,
        name="Dino Quest & Prehistoric Friends",
        target_age="3-8",
        description="Gentle dino adventures exploring T-Rex, Stegosaurus, Triceratops, and gentle giants.",
        educational_goal="Teach paleontology basics, prehistoric habitats, and natural history.",
        keywords=["cartoon dinosaur", "t-rex", "triceratops", "prehistoric jungle", "cute dino baby"],
        color_palette=["#2E7D32", "#558B2F", "#F9A825", "#8D6E63"],
        bg_style="jurassic_jungle",
    ),
    VideoTopic.SCIENCE_CURIOSITIES.value: TopicDefinition(
        id=VideoTopic.SCIENCE_CURIOSITIES.value,
        name="Everyday Science Miracles for Kids",
        target_age="4-8",
        description="Why the sky is blue, how rainbows appear, why rain falls, and how plants grow.",
        educational_goal="Encourage asking 'why', observation of the natural world, and critical thinking.",
        keywords=["rainbow", "laboratory cartoon", "magnifying glass", "science beaker", "sun and clouds"],
        color_palette=["#0288D1", "#26A69A", "#FFCA28", "#AB47BC"],
        bg_style="science_wonderland",
    ),
    VideoTopic.KIDS_JOKES_PUZZLES.value: TopicDefinition(
        id=VideoTopic.KIDS_JOKES_PUZZLES.value,
        name="Giggle Box: Silly Jokes & Brain Puzzles",
        target_age="3-8",
        description="Super funny, innocent knock-knock jokes, rhyming riddles, and smile-inducing puzzles.",
        educational_goal="Enhance language play, humor comprehension, and creative verbal thinking.",
        keywords=["happy laughing kid", "party confetti", "smiling cartoon face", "circus fun", "colorful balloons"],
        color_palette=["#FF4081", "#7C4DFF", "#536DFE", "#64FFDA"],
        bg_style="carnival_confetti",
    ),
}


def get_topic_definition(topic_id: str) -> TopicDefinition:
    """Return topic definition or fallback to animal riddles."""
    return TOPIC_CATALOG.get(topic_id, TOPIC_CATALOG[VideoTopic.ANIMAL_RIDDLES.value])
