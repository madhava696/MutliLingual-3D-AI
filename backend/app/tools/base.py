"""
Base tool interfaces and definitions for agentic tool execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    message: str
    data: Optional[Any] = None
    needs_confirmation: bool = False
    confirmation_payload: Optional[dict] = None


class BaseTool(ABC):
    """Abstract base class for all callable tools."""

    name: str
    description: str
    parameters_schema: dict
    is_deterministic: bool = True
    requires_confirmation: bool = False

    @abstractmethod
    async def execute(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute the tool logic."""
        pass
