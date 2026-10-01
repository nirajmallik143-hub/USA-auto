"""
Multi-topic rotation manager for US kids' content.
Ensures healthy thematic diversity across the 7 daily video slots and across days.
"""

from typing import List, Optional
from datetime import datetime, timezone

from src.config import VideoFormat, VideoTopic
from src.content.topics import TOPIC_CATALOG
from src.database.state_manager import StateManager, state_manager
from src.logger import logger


# All available 7 primary topics
ALL_TOPICS = [
    VideoTopic.ANIMAL_RIDDLES.value,
    VideoTopic.MORAL_STORIES.value,
    VideoTopic.ALPHABET_NUMBER_LEARNING.value,
    VideoTopic.SPACE_FACTS.value,
    VideoTopic.DINOSAUR_ADVENTURES.value,
    VideoTopic.SCIENCE_CURIOSITIES.value,
    VideoTopic.KIDS_JOKES_PUZZLES.value,
]

# Preferred format affinity for topics
LONG_PREFERRED_TOPICS = [
    VideoTopic.MORAL_STORIES.value,
    VideoTopic.SPACE_FACTS.value,
    VideoTopic.DINOSAUR_ADVENTURES.value,
    VideoTopic.SCIENCE_CURIOSITIES.value,
    VideoTopic.ALPHABET_NUMBER_LEARNING.value,
]

SHORTS_PREFERRED_TOPICS = [
    VideoTopic.ANIMAL_RIDDLES.value,
    VideoTopic.KIDS_JOKES_PUZZLES.value,
    VideoTopic.SPACE_FACTS.value,
    VideoTopic.SCIENCE_CURIOSITIES.value,
    VideoTopic.ALPHABET_NUMBER_LEARNING.value,
    VideoTopic.DINOSAUR_ADVENTURES.value,
    VideoTopic.MORAL_STORIES.value,
]


class TopicRotator:
    """Calculates and rotates topics for 5 Shorts + 2 Long videos daily."""

    def __init__(self, db: Optional[StateManager] = None):
        self.db = db or state_manager

    def get_daily_schedule_topics(self, date_str: Optional[str] = None) -> List[dict]:
        """
        Generate topic assignments for the 7 daily slots:
        - 5 Shorts (9:16)
        - 2 Long-form (16:9)
        """
        target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Calculate day of year offset to ensure variety day-by-day
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_offset = dt.timetuple().tm_yday

        # Select 2 distinct long topics
        long_index_1 = (day_offset * 2) % len(LONG_PREFERRED_TOPICS)
        long_index_2 = (day_offset * 2 + 1) % len(LONG_PREFERRED_TOPICS)
        if long_index_1 == long_index_2:
            long_index_2 = (long_index_1 + 1) % len(LONG_PREFERRED_TOPICS)

        long_topic_1 = LONG_PREFERRED_TOPICS[long_index_1]
        long_topic_2 = LONG_PREFERRED_TOPICS[long_index_2]

        # Select 5 shorts topics, shifting by day
        available_shorts = [t for t in ALL_TOPICS]
        shorts_topics = []
        for i in range(5):
            idx = (day_offset + i) % len(available_shorts)
            shorts_topics.append(available_shorts[idx])

        # Define 7 standard time-of-day slots
        # Pacing tailored for US family morning, noon, afternoon, evening
        slots = [
            {
                "slot_name": "slot_1_morning_short",
                "format": VideoFormat.SHORTS.value,
                "time": "08:00",
                "topic": shorts_topics[0],
                "description": "Morning wake-up short riddle/puzzle",
            },
            {
                "slot_name": "slot_2_morning_long",
                "format": VideoFormat.LONG.value,
                "time": "10:00",
                "topic": long_topic_1,
                "description": "Mid-morning educational long episode",
            },
            {
                "slot_name": "slot_3_lunch_short",
                "format": VideoFormat.SHORTS.value,
                "time": "12:00",
                "topic": shorts_topics[1],
                "description": "Lunchtime fun facts / joke short",
            },
            {
                "slot_name": "slot_4_afternoon_short",
                "format": VideoFormat.SHORTS.value,
                "time": "14:30",
                "topic": shorts_topics[2],
                "description": "Afternoon curiosity short",
            },
            {
                "slot_name": "slot_5_afterschool_long",
                "format": VideoFormat.LONG.value,
                "time": "16:30",
                "topic": long_topic_2,
                "description": "After-school story / deep-dive long episode",
            },
            {
                "slot_name": "slot_6_dinner_short",
                "format": VideoFormat.SHORTS.value,
                "time": "18:30",
                "topic": shorts_topics[3],
                "description": "Dinner-time interactive quiz short",
            },
            {
                "slot_name": "slot_7_bedtime_short",
                "format": VideoFormat.SHORTS.value,
                "time": "20:30",
                "topic": shorts_topics[4],
                "description": "Bedtime calm wonder riddle short",
            },
        ]
        return slots

    def select_next_topic(self, video_format: str, date_str: Optional[str] = None) -> str:
        """
        Dynamically pick a topic for an ad-hoc video, taking into account
        recent topics used today to avoid immediate duplicates.
        """
        target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing_jobs = self.db.get_jobs_by_date(target_date)
        used_topics = [j.topic for j in existing_jobs if j.video_format == video_format]

        candidates = LONG_PREFERRED_TOPICS if video_format == VideoFormat.LONG.value else ALL_TOPICS
        # Find topics not yet used today
        unused = [t for t in candidates if t not in used_topics]
        if unused:
            chosen = unused[0]
        else:
            # Fallback to least recently used
            chosen = candidates[len(used_topics) % len(candidates)]

        logger.info(f"Rotator selected '{chosen}' for format {video_format} on {target_date}")
        return chosen


topic_rotator = TopicRotator()
