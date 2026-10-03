"""
Configuration module for the automated video production and YouTube upload pipeline.
Loads settings from environment variables and .env file with validated types.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TEMPLATE = "template"


class TTSEngine(str, Enum):
    ELEVENLABS = "elevenlabs"
    GTTS = "gtts"


class VideoFormat(str, Enum):
    SHORTS = "shorts"
    LONG = "long"


class VideoTopic(str, Enum):
    ANIMAL_RIDDLES = "animal_riddles"
    MORAL_STORIES = "moral_stories"
    ALPHABET_NUMBER_LEARNING = "alphabet_number_learning"
    SPACE_FACTS = "space_facts"
    DINOSAUR_ADVENTURES = "dinosaur_adventures"
    SCIENCE_CURIOSITIES = "science_curiosities"
    KIDS_JOKES_PUZZLES = "kids_jokes_puzzles"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Application
    app_env: EnvironmentType = EnvironmentType.DEVELOPMENT
    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: Path = Path("logs")

    # Content Generation
    llm_provider: Optional[LLMProvider] = Field(default=None)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Voice / TTS
    tts_engine: Optional[TTSEngine] = Field(default=None, validation_alias=AliasChoices("tts_engine", "tts_provider"))
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default kid-friendly voice
    elevenlabs_model_id: str = "eleven_monolingual_v1"

    # Media assets
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None

    # YouTube Settings
    youtube_dry_run: bool = Field(
        default=True, validation_alias=AliasChoices("youtube_dry_run", "dry_run_upload")
    )
    youtube_client_secrets_file: Path = Path("secrets/client_secrets.json")
    youtube_credentials_file: Path = Path("secrets/youtube_credentials.json")
    youtube_privacy_status: str = "scheduled"  # "public", "private", "unlisted", "scheduled"
    youtube_made_for_kids: bool = Field(  # Mandatory COPPA designation
        default=True, validation_alias=AliasChoices("youtube_made_for_kids", "coppa_made_for_kids")
    )
    youtube_category_id: str = "27"  # 27 = Education, 24 = Entertainment

    # Daily Production & Schedule
    daily_shorts_target: int = 5
    daily_long_target: int = 2
    timezone: str = "America/New_York"
    max_job_retries: int = 3
    retry_backoff_seconds: int = 300
    auto_retry_failed: bool = True

    # Directories & Database
    database_url: str = "sqlite:///storage/pipeline.db"
    output_dir: Path = Path("output")
    storage_dir: Path = Path("storage")
    temp_dir: Path = Path("temp")

    # Celery / Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_llm_provider(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ("procedural", ""):
                return LLMProvider.TEMPLATE.value
        return value

    @model_validator(mode="after")
    def _auto_select_runtime_settings(self):
        """Select the default runtime provider only when the user leaves the setting unset."""
        if self.llm_provider is None:
            if self.openai_api_key:
                self.llm_provider = LLMProvider.OPENAI
            elif self.anthropic_api_key:
                self.llm_provider = LLMProvider.ANTHROPIC
            else:
                self.llm_provider = LLMProvider.TEMPLATE

        if self.tts_engine is None:
            if self.elevenlabs_api_key:
                self.tts_engine = TTSEngine.ELEVENLABS
            else:
                self.tts_engine = TTSEngine.GTTS

        return self

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        for directory in [self.log_dir, self.output_dir, self.storage_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()
settings.ensure_directories()
