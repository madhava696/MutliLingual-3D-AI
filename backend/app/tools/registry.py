"""
Pluggable Tool Registry for agentic task execution.
"""

from typing import Dict, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ToolResult
from app.tools.note_tool import DeleteNoteTool, ListNotesTool, SaveNoteTool
from app.tools.reminder_tool import CreateReminderTool, DeleteReminderTool, ListRemindersTool


class ToolRegistry:
    """Registry maintaining active system tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default Phase 2 deterministic productivity tools."""
        defaults = [
            CreateReminderTool(),
            ListRemindersTool(),
            DeleteReminderTool(),
            SaveNoteTool(),
            ListNotesTool(),
            DeleteNoteTool(),
        ]
        for tool in defaults:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Lookup a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """List all available tools."""
        return list(self._tools.values())

    async def execute_tool(
        self,
        name: str,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        **kwargs,
    ) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, message=f"Tool '{name}' not found.")
        return await tool.execute(db=db, session_id=session_id, language=language, **kwargs)


# Global singleton instance
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Return the global tool registry singleton."""
    return _registry
