"""
Application configuration — all settings loaded from environment variables.
Model names, provider keys, and feature flags are configuration, not code constants.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # --- Application ---
    APP_NAME: str = "AI Companion"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://companion:companion@localhost:5432/companion"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Session ---
    SESSION_TOKEN_BYTES: int = 48  # Length of secrets.token_urlsafe
    SESSION_TTL_MINUTES: int = 30  # Session inactivity timeout
    SESSION_MAX_CONTEXT_TURNS: int = 10  # Sliding window for conversation context

    # --- Rate Limiting ---
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_FILE_UPLOADS_PER_SESSION: int = 10

    # --- File Upload ---
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_CONTENT_TYPES: list[str] = ["application/pdf"]

    # --- LLM Provider (model names are CONFIG, not code) ---
    LLM_PROVIDER: str = "gemini"  # "gemini" | "openai"
    LLM_ECONOMICAL_MODEL: str = "gemini-2.0-flash"  # Placeholder — update after testing
    LLM_CAPABLE_MODEL: str = "gemini-2.0-pro"  # Placeholder — update after testing
    LLM_FALLBACK_MODEL: Optional[str] = None
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7

    # --- Provider API Keys ---
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # --- ASR / TTS (to be configured after provider evaluation) ---
    ASR_PROVIDER: str = "google"  # "google" | "sarvam" | "azure"
    TTS_PROVIDER: str = "google"  # "google" | "sarvam" | "azure"
    SARVAM_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_CREDENTIALS_PATH: Optional[str] = None

    # --- Web Search ---
    SEARCH_PROVIDER: str = "tavily"  # "tavily" | "serpapi"
    TAVILY_API_KEY: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Reminder Scheduler ---
    REMINDER_POLL_INTERVAL_SECONDS: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
