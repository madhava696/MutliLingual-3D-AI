"""
Provider factory — resolves the active ModelProvider based on configuration.
Supports Groq and Gemini with intelligent fallback.
"""

from functools import lru_cache

from app.config import get_settings
from app.providers.base import ModelProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider


@lru_cache()
def get_model_provider() -> ModelProvider:
    """Return configured model provider singleton."""
    settings = get_settings()
    provider_name = settings.LLM_PROVIDER.lower()

    google_key = settings.GOOGLE_API_KEY or ""
    openai_key = settings.OPENAI_API_KEY or ""
    groq_key = settings.GROQ_API_KEY or ""

    # Detect Groq key even if placed in GOOGLE_API_KEY or OPENAI_API_KEY
    has_groq_key = bool(
        groq_key
        or google_key.startswith("gsk_")
        or openai_key.startswith("gsk_")
    )

    if provider_name == "groq" or has_groq_key:
        active_groq_key = groq_key or (google_key if google_key.startswith("gsk_") else openai_key)
        return GroqProvider(api_key=active_groq_key)

    if provider_name == "gemini" and google_key and not google_key.startswith("gsk_"):
        return GeminiProvider(api_key=google_key)

    # Default: if has groq key, use Groq; otherwise Gemini
    if has_groq_key:
        return GroqProvider(api_key=groq_key or google_key or openai_key)

    return GeminiProvider(api_key=google_key)
