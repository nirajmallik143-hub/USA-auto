"""
COPPA compliance and kid-safety validation for YouTube uploads.
Ensures mandatory 'Made for Kids' audience designation and child-safe metadata.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple
from src.config import VideoFormat, VideoTopic, settings
from src.logger import logger


# Safety blocklist: forbidden terms for US kids content
FORBIDDEN_KIDS_TERMS = {
    "kill", "death", "blood", "murder", "gun", "weapon", "war", "fight",
    "scary", "horror", "monster", "nightmare", "curse", "demon", "evil",
    "sexy", "gamble", "casino", "beer", "wine", "drug", "alcohol"
}


@dataclass
class ComplianceResult:
    is_compliant: bool
    made_for_kids: bool
    category_id: str
    reasons: List[str]


class KidSafetyComplianceValidator:
    """Validates COPPA compliance and YouTube 'Made for Kids' mandates."""

    def __init__(self):
        pass

    def validate_metadata(
        self,
        title: str,
        description: str,
        tags: List[str],
        topic: str,
    ) -> ComplianceResult:
        """
        Validate that all video metadata meets COPPA and YouTube Kids guidelines:
        1. Mandatory Made For Kids flag is enabled.
        2. No prohibited, scary, or unsafe terms.
        3. Appropriate category assigned (27=Education, 24=Entertainment).
        """
        reasons = []
        is_compliant = True

        # Check Made For Kids requirement
        if not settings.youtube_made_for_kids:
            is_compliant = False
            reasons.append("Mandatory COPPA requirement failed: YOUTUBE_MADE_FOR_KIDS must be True")

        # Scan for forbidden words in title, description, and tags using regex word boundaries
        text_corpus = f"{title} {description} {' '.join(tags)}"
        for word in FORBIDDEN_KIDS_TERMS:
            if re.search(r"\b" + re.escape(word) + r"\b", text_corpus, re.IGNORECASE):
                is_compliant = False
                reasons.append(f"Forbidden term detected in kids metadata: '{word}'")

        # Determine Category ID
        category_id = self.resolve_category_id(topic)

        if is_compliant:
            logger.info("Content passed COPPA & YouTube Kids safety compliance check.")
        else:
            logger.warning(f"Compliance issues detected: {'; '.join(reasons)}")

        return ComplianceResult(
            is_compliant=is_compliant,
            made_for_kids=True,  # Always enforced for kids channel
            category_id=category_id,
            reasons=reasons,
        )

    def resolve_category_id(self, topic: str) -> str:
        """
        YouTube Category IDs:
        27 = Education
        24 = Entertainment
        15 = Pets & Animals
        """
        if topic == VideoTopic.ANIMAL_RIDDLES.value:
            return "15"  # Pets & Animals or 27
        elif topic in [VideoTopic.MORAL_STORIES.value, VideoTopic.KIDS_JOKES_PUZZLES.value]:
            return "24"  # Entertainment
        else:
            return "27"  # Education (Default)


compliance_validator = KidSafetyComplianceValidator()
