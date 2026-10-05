"""Pydantic schemas for usage API."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UsageLogEntry(BaseModel):
    """Single usage log entry."""
    id: uuid.UUID
    provider: str
    model: str
    task_type: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    latency_ms: Optional[int]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageByProvider(BaseModel):
    """Aggregated usage per provider."""
    provider: str
    total_cost_usd: float
    total_requests: int


class UsageByTask(BaseModel):
    """Aggregated usage per task type."""
    task_type: str
    total_cost_usd: float
    total_requests: int


class UsageSummaryResponse(BaseModel):
    """Aggregated usage summary for a session."""
    total_cost_usd: float
    total_requests: int
    by_provider: list[UsageByProvider]
    by_task: list[UsageByTask]
