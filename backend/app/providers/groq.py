"""
Groq LLM provider adapter using httpx.
Supports high-speed completions, streaming, and Whisper speech transcription.
"""

import json
import logging
import time
from typing import AsyncGenerator, Optional

import httpx

from app.config import get_settings
from app.providers.base import LLMChunk, LLMResponse, ModelProvider, ModelTier

logger = logging.getLogger(__name__)


class GroqProvider(ModelProvider):
    """Groq API provider adapter for ultra-fast multilingual inference."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.GROQ_API_KEY or settings.GOOGLE_API_KEY or settings.OPENAI_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"

    def _resolve_model(self, tier: ModelTier) -> str:
        settings = get_settings()
        if settings.LLM_PROVIDER.lower() == "groq" and "gemini" not in settings.LLM_ECONOMICAL_MODEL.lower():
            if tier == ModelTier.CAPABLE:
                return settings.LLM_CAPABLE_MODEL
            if tier == ModelTier.FALLBACK:
                return settings.LLM_FALLBACK_MODEL or settings.LLM_ECONOMICAL_MODEL
            return settings.LLM_ECONOMICAL_MODEL

        # Defaults for Groq
        if tier == ModelTier.CAPABLE:
            return "openai/gpt-oss-120b"
        return "qwen/qwen3.8-27b"

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

        if not self.api_key:
            latency = int((time.perf_counter() - start_time) * 1000)
            fallback = (
                f"[AI Companion - {model_name}] I received your message: \"{prompt}\". "
                "Please configure GROQ_API_KEY in .env for live intelligence."
            )
            return LLMResponse(
                text=fallback,
                input_tokens=len(prompt.split()),
                output_tokens=len(fallback.split()),
                model_name=model_name,
                provider="groq_mock",
                latency_ms=latency,
            )

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if res.status_code != 200:
                    logger.error(f"Groq API returned error {res.status_code}: {res.text}")
                    # Try alternative standard Groq models if model not found
                    if "model_not_found" in res.text or "does not exist" in res.text or res.status_code == 404:
                        alt_model = "openai/gpt-oss-120b" if payload["model"] == "qwen/qwen3.8-27b" else "qwen/qwen3.8-27b"
                        payload["model"] = alt_model
                        res = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers=headers,
                            json=payload,
                        )

                res.raise_for_status()
                data = res.json()

            latency = int((time.perf_counter() - start_time) * 1000)
            choice = data["choices"][0]
            text = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})

            return LLMResponse(
                text=text,
                input_tokens=usage.get("prompt_tokens", len(prompt.split())),
                output_tokens=usage.get("completion_tokens", len(text.split())),
                model_name=data.get("model", model_name),
                provider="groq",
                latency_ms=latency,
                finish_reason=choice.get("finish_reason", "stop"),
            )

        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            latency = int((time.perf_counter() - start_time) * 1000)
            return LLMResponse(
                text=f"I encountered an error connecting to the model: {e}",
                input_tokens=len(prompt.split()),
                output_tokens=10,
                model_name=model_name,
                provider="groq",
                latency_ms=latency,
            )

    async def stream_generate(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.ECONOMICAL,
        system_instruction: Optional[str] = None,
    ) -> AsyncGenerator[LLMChunk, None]:
        """Stream response chunks in real-time using SSE."""
        model_name = self._resolve_model(tier)
        settings = get_settings()

        if not self.api_key:
            yield LLMChunk(text=f"[AI Companion] Ready for conversation. Please configure GROQ_API_KEY.", is_final=True)
            return

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield LLMChunk(text="", is_final=True)
                            break
                        try:
                            chunk_json = json.loads(data_str)
                            delta = chunk_json["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield LLMChunk(text=content, is_final=False)
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            yield LLMChunk(text=f"\n[Streaming error: {e}]", is_final=True)

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language: Optional[str] = None) -> str:
        """Transcribe speech using Groq Whisper API."""
        if not self.api_key:
            raise ValueError("Groq API key not configured")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": "whisper-large-v3-turbo"}
        if language in ("en", "te", "hi"):
            data["language"] = language

        # Detect audio mime type based on filename extension
        content_type = "audio/wav"
        lower_name = filename.lower()
        if lower_name.endswith(".webm"):
            content_type = "audio/webm"
        elif lower_name.endswith(".mp3"):
            content_type = "audio/mp3"
        elif lower_name.endswith(".m4a") or lower_name.endswith(".mp4"):
            content_type = "audio/mp4"
        elif lower_name.endswith(".ogg"):
            content_type = "audio/ogg"

        files = {"file": (filename, audio_bytes, content_type)}

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                data=data,
                files=files,
            )
            if res.status_code != 200:
                # Fallback to standard whisper-large-v3 if turbo is unavailable
                data["model"] = "whisper-large-v3"
                files = {"file": (filename, audio_bytes, content_type)}
                res = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    data=data,
                    files=files,
                )
            res.raise_for_status()
            result = res.json()
            return result.get("text", "")
