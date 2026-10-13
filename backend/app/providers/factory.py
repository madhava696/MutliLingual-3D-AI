"""
Provider factory — resolves the active ModelProvider based on configuration.
"""

from functools import lru_cache

from app.config import get_settings
from app.providers.base import ModelProvider
from app.providers.gemini import GeminiProvider


@lru_cache()
def get_model_provider() -> ModelProvider:
    """Return configured model provider singleton."""
    settings = get_settings()
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "gemini":
        return GeminiProvider(api_key=settings.GOOGLE_API_KEY)

    # Default to GeminiProvider
    return GeminiProvider(api_key=settings.GOOGLE_API_KEY)
