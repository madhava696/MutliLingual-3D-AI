"""
Google Gemini provider adapter using the modern google-genai SDK.
Model tiers and keys are loaded dynamically from application Settings.
"""

import logging
import time
from typing import AsyncGenerator, Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.providers.base import LLMChunk, LLMResponse, ModelProvider, ModelTier

logger = logging.getLogger(__name__)


class GeminiProvider(ModelProvider):
    """Google Gemini provider adapter supporting streaming and non-streaming generation."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def _resolve_model(self, tier: ModelTier) -> str:
        """Resolve model name from configuration based on tier."""
        settings = get_settings()
        if tier == ModelTier.CAPABLE:
            return settings.LLM_CAPABLE_MODEL
        if tier == ModelTier.FALLBACK:
            return settings.LLM_FALLBACK_MODEL or settings.LLM_ECONOMICAL_MODEL
        return settings.LLM_ECONOMICAL_MODEL

    async def generate(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.ECONOMICAL,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        """Generate complete text response with latency and token tracking."""
        model_name = self._resolve_model(tier)
        settings = get_settings()
        start_time = time.perf_counter()

        if not self.client:
            # Offline / Mock Fallback if API key is not configured
            logger.warning("GOOGLE_API_KEY not configured. Using conversational fallback mode.")
            latency = int((time.perf_counter() - start_time) * 1000)
            fallback_text = (
                f"[AI Companion - {model_name}] I received your message: \"{prompt}\". "
                "Please configure GOOGLE_API_KEY in .env for live Gemini intelligence."
            )
            return LLMResponse(
                text=fallback_text,
                input_tokens=len(prompt.split()),
                output_tokens=len(fallback_text.split()),
                model_name=model_name,
                provider="gemini_mock",
                latency_ms=latency,
            )

        try:
            config = types.GenerateContentConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_TOKENS,
                system_instruction=system_instruction,
            )
            response = await self.client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            latency = int((time.perf_counter() - start_time) * 1000)
            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

            return LLMResponse(
                text=response.text or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=model_name,
                provider="gemini",
                latency_ms=latency,
            )

        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            latency = int((time.perf_counter() - start_time) * 1000)
            return LLMResponse(
                text=f"I encountered an error connecting to the model: {e}",
                input_tokens=len(prompt.split()),
                output_tokens=10,
                model_name=model_name,
                provider="gemini",
                latency_ms=latency,
                finish_reason="error",
            )

    async def stream_generate(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.ECONOMICAL,
        system_instruction: Optional[str] = None,
    ) -> AsyncGenerator[LLMChunk, None]:
        """Stream chunks from Gemini in real-time."""
        model_name = self._resolve_model(tier)
        settings = get_settings()

        if not self.client:
            # Simulated stream in offline mode
            fallback_text = (
                f"[AI Companion - {model_name}] I received your message: \"{prompt}\". "
                "Configure GOOGLE_API_KEY in .env for live streaming."
            )
            words = fallback_text.split(" ")
            for i, word in enumerate(words):
                yield LLMChunk(text=word + " ", is_final=(i == len(words) - 1))
            return

        try:
            config = types.GenerateContentConfig(
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_TOKENS,
                system_instruction=system_instruction,
            )
            response_stream = await self.client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=config,
            )

            async for chunk in response_stream:
                if chunk.text:
                    yield LLMChunk(text=chunk.text, is_final=False)

            yield LLMChunk(text="", is_final=True)

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            yield LLMChunk(text=f"Error streaming response: {e}", is_final=True)
