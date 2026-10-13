"""
Cost tracking and usage telemetry.
Calculates token-to-USD costs and persists anonymized metrics to UsageLog.
"""

import logging
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog

logger = logging.getLogger(__name__)

# Model pricing in USD per 1M tokens
MODEL_PRICING = {
    # Gemini 2.0 Flash
    "gemini-2.0-flash": {"input_per_million": 0.10, "output_per_million": 0.40},
    # Gemini 2.0 Pro
    "gemini-2.0-pro": {"input_per_million": 1.25, "output_per_million": 5.00},
    # Default fallback
    "default": {"input_per_million": 0.15, "output_per_million": 0.60},
}


def calculate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate estimated cost in USD based on model pricing."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]
    return round(input_cost + output_cost, 6)


async def record_usage_log(
    db: AsyncSession,
    session_id: Optional[uuid.UUID],
    provider: str,
    model: str,
    task_type: str,
    input_tokens: Optional[int] = 0,
    output_tokens: Optional[int] = 0,
    estimated_cost_usd: Optional[float] = 0.0,
    latency_ms: Optional[int] = 0,
    status: str = "success",
) -> UsageLog:
    """Persist an anonymized operational usage log entry."""
    log = UsageLog(
        session_id=session_id,
        provider=provider,
        model=model,
        task_type=task_type,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        latency_ms=latency_ms,
        status=status,
    )
    db.add(log)
    try:
        await db.flush()
    except Exception as e:
        logger.error(f"Failed to record usage log: {e}")
    return log
