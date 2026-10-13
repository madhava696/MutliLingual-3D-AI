"""
Note tools: create, list, and delete notes.
Executes deterministically without incurring LLM token costs.
"""

from typing import Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import note_service
from app.tools.base import BaseTool, ToolResult


class SaveNoteTool(BaseTool):
    name = "note_save"
    description = "Save a new note for the current session."
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title or headline of the note"},
            "content": {"type": "string", "description": "The note content to store"},
        },
        "required": ["content"],
    }
    is_deterministic = True
    requires_confirmation = False

    async def execute(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        content: str,
        title: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        note_title = title or (content[:30] + "..." if len(content) > 30 else content)
        note = await note_service.create_note(
            db=db,
            session_id=session_id,
            title=note_title,
            content=content,
            language=language,
            source_type="manual",
        )

        if language == "te":
            msg = f"నోట్ సేవ్ చేయబడింది: '{note_title}'."
        elif language == "hi":
            msg = f"नोट सुरक्षित कर लिया गया है: '{note_title}'."
        else:
            msg = f"Note saved: '{note_title}'."

        return ToolResult(
            success=True,
            message=msg,
            data={"note_id": str(note.id), "title": note.title},
        )


class ListNotesTool(BaseTool):
    name = "note_list"
    description = "List all stored notes for the current session."
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
        notes = await note_service.get_notes_by_session(db, session_id)
        if not notes:
            if language == "te":
                msg = "ప్రస్తుతానికి ఎటువంటి నోట్స్ లేవు."
            elif language == "hi":
                msg = "वर्तमान में कोई नोट्स नहीं हैं।"
            else:
                msg = "You have no saved notes."
            return ToolResult(success=True, message=msg, data=[])

        note_entries = [f"• {n.title}: {n.content[:50]}" for n in notes]
        msg_header = "మీ నోట్స్:" if language == "te" else "आपके नोट्स:" if language == "hi" else "Here are your notes:"
        msg = f"{msg_header}\n" + "\n".join(note_entries)

        return ToolResult(
            success=True,
            message=msg,
            data=[{"id": str(n.id), "title": n.title, "content": n.content} for n in notes],
        )


class DeleteNoteTool(BaseTool):
    name = "note_delete"
    description = "Delete a note by ID (requires user confirmation)."
    parameters_schema = {
        "type": "object",
        "properties": {
            "note_id": {"type": "string", "description": "The UUID of the note to delete"},
        },
        "required": ["note_id"],
    }
    is_deterministic = True
    requires_confirmation = True

    async def execute(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        language: str,
        note_id: str,
        confirmed: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            n_uuid = uuid.UUID(note_id)
        except ValueError:
            return ToolResult(success=False, message="Invalid note ID format.")

        note = await note_service.get_note_by_id(db, n_uuid)
        if not note or note.session_id != session_id:
            return ToolResult(success=False, message="Note not found.")

        if not confirmed:
            return ToolResult(
                success=True,
                message=f"Are you sure you want to delete note '{note.title}'?",
                needs_confirmation=True,
                confirmation_payload={"tool": self.name, "note_id": note_id},
            )

        await note_service.delete_note(db, note)
        return ToolResult(success=True, message=f"Note '{note.title}' deleted successfully.")
