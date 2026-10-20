"""
File and PDF management API endpoints.
Handles PDF upload, text extraction with pypdf, AI analysis/summarization, and deletion.
"""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
import pypdf
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.middleware.session_auth import get_authenticated_session
from app.models.file import UploadedFile
from app.models.session import Session
from app.providers.base import ModelTier
from app.providers.factory import get_model_provider
from app.services import note_service

router = APIRouter(prefix="/files", tags=["files"])


class FileResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: str
    page_count: Optional[int] = None
    extracted_text_preview: Optional[str] = None


class FileAnalysisRequest(BaseModel):
    question: Optional[str] = "Summarize the key points of this document."
    save_as_note: Optional[bool] = False


class FileAnalysisResponse(BaseModel):
    file_id: uuid.UUID
    analysis: str
    model_used: str
    note_id: Optional[uuid.UUID] = None


def extract_pdf_text(storage_path: str, max_chars: int = 15000) -> tuple[str, int]:
    """Extract text and page count from PDF using pypdf."""
    try:
        reader = pypdf.PdfReader(storage_path)
        pages_count = len(reader.pages)
        full_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text.append(t)
        extracted = "\n".join(full_text)
        return extracted[:max_chars], pages_count
    except Exception as e:
        return f"[Text extraction failed: {e}]", 0


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: uuid.UUID = Form(...),
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF document.
    Validates size and MIME type, saves to disk, extracts text, and registers in DB.
    """
    settings = get_settings()

    if session_id != session.id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    if not file.filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are currently supported.",
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.",
        )

    # Save to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = uuid.uuid4()
    safe_filename = f"{file_id}_{file.filename}"
    storage_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(storage_path, "wb") as f:
        f.write(content)

    # Extract text with pypdf
    extracted_text, page_count = extract_pdf_text(storage_path)

    # Register in DB
    uploaded_file = UploadedFile(
        id=file_id,
        session_id=session.id,
        filename=file.filename,
        content_type=file.content_type or "application/pdf",
        storage_path=storage_path,
        size_bytes=len(content),
    )
    db.add(uploaded_file)
    await db.commit()
    await db.refresh(uploaded_file)

    return FileResponse(
        id=uploaded_file.id,
        session_id=uploaded_file.session_id,
        filename=uploaded_file.filename,
        content_type=uploaded_file.content_type,
        size_bytes=uploaded_file.size_bytes,
        created_at=uploaded_file.created_at.isoformat(),
        page_count=page_count,
        extracted_text_preview=extracted_text[:400] + ("..." if len(extracted_text) > 400 else ""),
    )


@router.get("", response_model=list[FileResponse])
async def list_files(
    session_id: uuid.UUID = Query(...),
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded files for the authenticated session."""
    if session_id != session.id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    res = await db.execute(
        select(UploadedFile).where(UploadedFile.session_id == session.id).order_by(UploadedFile.created_at.desc())
    )
    files = res.scalars().all()
    out = []
    for f in files:
        preview = ""
        pages = 0
        if os.path.exists(f.storage_path):
            text, pages = extract_pdf_text(f.storage_path, max_chars=400)
            preview = text
        out.append(
            FileResponse(
                id=f.id,
                session_id=f.session_id,
                filename=f.filename,
                content_type=f.content_type,
                size_bytes=f.size_bytes,
                created_at=f.created_at.isoformat(),
                page_count=pages,
                extracted_text_preview=preview,
            )
        )
    return out


@router.post("/{file_id}/analyze", response_model=FileAnalysisResponse)
async def analyze_file(
    file_id: uuid.UUID,
    body: FileAnalysisRequest,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze or query an uploaded PDF using the active LLM provider.
    Can optionally save the generated summary/answer as a Note with source_type='pdf_summary'.
    """
    res = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id, UploadedFile.session_id == session.id)
    )
    uploaded = res.scalar_one_or_none()
    if not uploaded:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(uploaded.storage_path):
        raise HTTPException(status_code=404, detail="File content not found on server")

    text, _ = extract_pdf_text(uploaded.storage_path, max_chars=12000)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from this PDF.")

    provider = get_model_provider()
    system_instruction = (
        f"You are an expert document assistant. You are analyzing the document '{uploaded.filename}'. "
        f"Answer in the user's preferred language ({session.language}). Be clear, structured, and helpful."
    )
    prompt = (
        f"Document Content:\n\"\"\"\n{text}\n\"\"\"\n\n"
        f"User Request: {body.question}"
    )

    llm_resp = await provider.generate(
        prompt=prompt,
        tier=ModelTier.CAPABLE,
        system_instruction=system_instruction,
    )

    note_id = None
    if body.save_as_note:
        note = await note_service.create_note(
            db=db,
            session_id=session.id,
            title=f"Summary: {uploaded.filename}",
            content=llm_resp.text,
            language=session.language,
            source_type="pdf_summary",
        )
        note_id = note.id

    return FileAnalysisResponse(
        file_id=uploaded.id,
        analysis=llm_resp.text,
        model_used=llm_resp.model_name,
        note_id=note_id,
    )


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: uuid.UUID,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Delete uploaded file from DB and disk."""
    res = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id, UploadedFile.session_id == session.id)
    )
    uploaded = res.scalar_one_or_none()
    if not uploaded:
        raise HTTPException(status_code=404, detail="File not found")

    if os.path.exists(uploaded.storage_path):
        try:
            os.remove(uploaded.storage_path)
        except OSError:
            pass

    await db.delete(uploaded)
    await db.commit()
    return {"deleted": True}
