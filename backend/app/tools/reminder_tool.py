"""
Reminder tools: create, list, and delete reminders.
Executes deterministically without incurring LLM token costs.
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import reminder_service
from app.tools.base import BaseTool, ToolResult


def parse_datetime_hint(hint: Optional[str]) -> datetime:
    """Helper to parse relative or formatted time hints, defaulting to 1 hour from now."""
    now = datetime.now(timezone.utc)
    if not hint:
        return now + timedelta(hours=1)

    hint_lower = hint.lower().strip()

    # e.g., "in 10 minutes", "in 30 mins"
    match_min = re.search(r"(\d+)\s*(?:minute|min)", hint_lower)
    if match_min:
        return now + timedelta(minutes=int(match_min.group(1)))

    # e.g., "in 2 hours", "in 1 hr"
    match_hr = re.search(r"(\d+)\s*(?:hour|hr)", hint_lower)
    if match_hr:
        return now + timedelta(hours=int(match_hr.group(1)))

    # e.g., "tomorrow"
    if "tomorrow" in hint_lower or "రేపు" in hint_lower or "कल" in hint_lower:
        return now + timedelta(days=1)

    # ISO format fallback
    try:
        return datetime.fromisoformat(hint)
    except Exception:
        return now + timedelta(hours=1)


class CreateReminderTool(BaseTool):
    name = "reminder_create"
    description = "Create a new reminder scheduled for a specific time."
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The title or action of the reminder"},
            "time_hint": {"type": "string", "description": "When to remind (e.g. '5 PM', 'in 30 mins', 'tomorrow')"},
            "description": {"type": "string", "description": "Optional notes or details"},
        },
        "required": ["title"],
    }
    is_deterministic = True
    requires_confirmation = False

    async def execute(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        title: str,
        time_hint: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        remind_at = parse_datetime_hint(time_hint)
        reminder = await reminder_service.create_reminder(
            db=db,
            session_id=session_id,
            title=title,
            remind_at=remind_at,
            description=description,
            language=language,
        )

        formatted_time = remind_at.strftime("%I:%M %p UTC")
        if language == "te":
            msg = f"రిమైండర్ సెట్ చేయబడింది: '{title}' ({formatted_time}కి)."
        elif language == "hi":
            msg = f"रिमाइंडर सेट कर दिया गया है: '{title}' ({formatted_time} पर)."
        else:
            msg = f"Reminder scheduled: '{title}' for {formatted_time}."

        return ToolResult(
            success=True,
            message=msg,
            data={"reminder_id": str(reminder.id), "title": reminder.title, "remind_at": reminder.remind_at.isoformat()},
        )


class ListRemindersTool(BaseTool):
    name = "reminder_list"
    description = "List all existing reminders for this session."
    parameters_schema = {"type": "object", "properties": {}}
    is_deterministic = True
    requires_confirmation = False

    async def execute(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        **kwargs: Any,
    ) -> ToolResult:
        reminders = await reminder_service.get_reminders_by_session(db, session_id)
        if not reminders:
            if language == "te":
                msg = "ప్రస్తుతానికి ఎటువంటి రిమైండర్లు లేవు."
            elif language == "hi":
                msg = "वर्तमान में कोई रिमाइंडर नहीं हैं।"
            else:
                msg = "You have no scheduled reminders."
            return ToolResult(success=True, message=msg, data=[])

        reminder_titles = [f"• {r.title} ({r.remind_at.strftime('%I:%M %p')})" for r in reminders]
        msg_header = "మీ రిమైండర్లు:" if language == "te" else "आपके रिमाइंडर्स:" if language == "hi" else "Here are your reminders:"
        msg = f"{msg_header}\n" + "\n".join(reminder_titles)

        return ToolResult(
            success=True,
            message=msg,
            data=[{"id": str(r.id), "title": r.title, "status": r.status} for r in reminders],
        )


class DeleteReminderTool(BaseTool):
    name = "reminder_delete"
    description = "Delete a reminder by ID (requires user confirmation)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "reminder_id": {"type": "string", "description": "The UUID of the reminder to delete"},
        },
        "required": ["reminder_id"],
    }
    is_deterministic = True
    requires_confirmation = True

    async def execute(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        reminder_id: str,
        confirmed: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            r_uuid = uuid.UUID(reminder_id)
        except ValueError:
            return ToolResult(success=False, message="Invalid reminder ID format.")

        reminder = await reminder_service.get_reminder_by_id(db, r_uuid)
        if not reminder or reminder.session_id != session_id:
            return ToolResult(success=False, message="Reminder not found.")

        if not confirmed:
            return ToolResult(
                success=True,
                message=f"Are you sure you want to delete the reminder '{reminder.title}'?",
                needs_confirmation=True,
                confirmation_payload={"tool": self.name, "reminder_id": reminder_id},
            )

        await reminder_service.delete_reminder(db, reminder)
        return ToolResult(success=True, message=f"Reminder '{reminder.title}' deleted successfully.")
