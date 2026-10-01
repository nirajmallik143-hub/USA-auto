"""
SEO optimization engine for US kids' YouTube videos.
Optimizes titles, structured descriptions with chapter timestamps, and tags.
"""

from typing import List, Optional
from src.config import VideoFormat, VideoTopic
from src.content.script_generator import ScriptData
from src.content.topics import get_topic_definition
from src.logger import logger


DEFAULT_KIDS_TAGS = [
    "kids learning", "educational videos for kids", "family friendly",
    "toddler fun", "preschool learning", "nursery rhymes", "kids cartoons",
    "fun stories for kids", "learning for children"
]


class KidsSEOOptimizer:
    """Generates SEO-rich, compliant YouTube metadata."""

    def optimize_title(self, raw_title: str, video_format: str, topic: str) -> str:
        """
        Optimize title for high click-through rate while maintaining kid friendliness.
        """
        title = raw_title.strip()
        if video_format == VideoFormat.SHORTS.value:
            if "#Shorts" not in title:
                title = f"{title} #Shorts"
            # Ensure under 70 characters for mobile display
            if len(title) > 70:
                title = title[:67].rsplit(" ", 1)[0] + " #Shorts"
        else:
            # Long-form
            if len(title) > 85:
                title = title[:82].rsplit(" ", 1)[0] + "..."

        return title

    def optimize_description(
        self,
        raw_description: str,
        script: ScriptData,
    ) -> str:
        """
        Build full SEO description with chapter timestamps and family-safe notices.
        """
        parts = [raw_description.strip(), ""]

        # Add Chapters for Long-Form
        if script.video_format == VideoFormat.LONG.value and script.chapters:
            parts.append("TIMESTAMPS:")
            for ch in script.chapters:
                parts.append(f"{ch.get('time', '00:00')} - {ch.get('title', 'Chapter')}")
            parts.append("")

        # Add educational values
        topic_def = get_topic_definition(script.topic)
        parts.append(f"Educational Focus: {topic_def.educational_goal}")
        parts.append(f"Target Age: Ages {topic_def.target_age}")
        parts.append("")

        # Mandatory Family Safety & COPPA Disclaimer
        parts.append("=========================================")
        parts.append("SAFETY & FAMILY COMPLIANCE NOTICE:")
        parts.append("This video has been specifically created for kids and families!")
        parts.append("Compliant with COPPA and YouTube Kids community guidelines.")
        parts.append("Safe, wholesome, educational, and fun for all ages.")
        parts.append("=========================================")
        parts.append("")

        # Safe hashtags
        topic_tag = f"#{script.topic.replace('_', '').capitalize()}"
        if script.video_format == VideoFormat.SHORTS.value:
            parts.append(f"#Shorts #KidsLearning #PreschoolFun {topic_tag} #KidsStories")
        else:
            parts.append(f"#KidsEducation #LearningForKids #FamilyEntertainment {topic_tag} #StoryTime")

        return "\n".join(parts)

    def optimize_tags(self, raw_tags: List[str], topic: str) -> List[str]:
        """Combine specific tags with top-ranking family-safe tags."""
        tags = list(dict.fromkeys(raw_tags + DEFAULT_KIDS_TAGS))
        topic_def = get_topic_definition(topic)
        tags.extend(topic_def.keywords)
        # Deduplicate and cap at 15 tags
        unique_tags = []
        for t in tags:
            clean = t.strip().lower()
            if clean and clean not in unique_tags:
                unique_tags.append(clean)
            if len(unique_tags) >= 15:
                break
        return unique_tags


seo_optimizer = KidsSEOOptimizer()
