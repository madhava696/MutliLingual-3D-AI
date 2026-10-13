"""
Abstract ModelProvider interface.
Encapsulates LLM providers (Gemini, OpenAI, Fallback) and ensures
model names are runtime configurations, not code constants.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Optional


class ModelTier(str, Enum):
    """Model capability tiers defined in the development plan."""
    ECONOMICAL = "economical"  # Low-cost, fast (e.g. Gemini 2.0 Flash)
    CAPABLE = "capable"        # High-capability, reasoning (e.g. Gemini 2.0 Pro)
    FALLBACK = "fallback"      # Secondary provider on error/timeout


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    text: str
    input_tokens: int
    output_tokens: int
    model_name: str
    provider: str
    latency_ms: int
    finish_reason: Optional[str] = "stop"


@dataclass
class LLMChunk:
    """Streaming chunk from LLM provider."""
    text: str
    is_final: bool = False


class ModelProvider(ABC):
    """Abstract interface that all LLM providers must implement."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.ECONOMICAL,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        """Generate a complete text response."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.ECONOMICAL,
        system_instruction: Optional[str] = None,
    ) -> AsyncGenerator[LLMChunk, None]:
        """Stream response chunks in real-time."""
        pass
