"""
Data models and status enums for pipeline state tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_VOICE = "generating_voice"
    GENERATING_ASSETS = "generating_assets"
    ASSEMBLING_VIDEO = "assembling_video"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VideoJob:
    id: str
    video_format: str  # "shorts" or "long"
    topic: str
    slot_name: str
    scheduled_time: str
    status: JobStatus = JobStatus.PENDING
    attempt_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    script_data: Optional[Dict[str, Any]] = None
    video_path: Optional[str] = None
    duration_seconds: float = 0.0
    youtube_id: Optional[str] = None
    youtube_url: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


@dataclass
class DailyQuota:
    date: str  # YYYY-MM-DD
    target_shorts: int = 5
    target_long: int = 2
    completed_shorts: int = 0
    completed_long: int = 0
    failed_shorts: int = 0
    failed_long: int = 0

    @property
    def shorts_needed(self) -> int:
        return max(0, self.target_shorts - self.completed_shorts)

    @property
    def long_needed(self) -> int:
        return max(0, self.target_long - self.completed_long)

    @property
    def is_quota_met(self) -> bool:
        return self.shorts_needed == 0 and self.long_needed == 0
