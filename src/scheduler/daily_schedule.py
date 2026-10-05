"""
Daily schedule configuration for 7 videos (5 Shorts + 2 Long) per day.
Aligns with US peak viewing hours for kids and family audiences.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional
import zoneinfo

from src.config import VideoFormat, settings
from src.content.topic_rotator import topic_rotator


PREPARATION_MINUTES = 60


@dataclass
class ScheduledSlot:
    slot_id: str
    slot_name: str
    video_format: str
    time_str: str  # "HH:MM"
    topic: str
    description: str

    def get_scheduled_datetime(self, target_date: Optional[str] = None) -> datetime:
        """Calculate target ISO timestamp in configured timezone."""
        date_str = target_date or datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
        hour, minute = map(int, self.time_str.split(":"))
        tz = zoneinfo.ZoneInfo(settings.timezone)
        local_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=hour, minute=minute, second=0, microsecond=0, tzinfo=tz
        )
        return local_dt

    def get_preparation_datetime(self, target_date: Optional[str] = None) -> datetime:
        """Start production early enough to schedule upload for the release time."""
        return self.get_scheduled_datetime(target_date) - timedelta(minutes=PREPARATION_MINUTES)


class DailyScheduleManager:
    """Manages the 7 daily publishing slots for US kids content."""

    def __init__(self):
        pass

    def get_slots_for_date(self, target_date: Optional[str] = None) -> List[ScheduledSlot]:
        """Generate the 7 configured slots for a specific date with dynamic topic rotation."""
        date_str = target_date or datetime.now(zoneinfo.ZoneInfo(settings.timezone)).strftime("%Y-%m-%d")
        slot_dicts = topic_rotator.get_daily_schedule_topics(date_str)

        slots = []
        for s in slot_dicts:
            slots.append(
                ScheduledSlot(
                    slot_id=f"{date_str}_{s['slot_name']}",
                    slot_name=s["slot_name"],
                    video_format=s["format"],
                    time_str=s["time"],
                    topic=s["topic"],
                    description=s["description"],
                )
            )
        return slots


daily_schedule = DailyScheduleManager()
