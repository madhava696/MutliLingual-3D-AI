"""
Audio API endpoints.
Provides speech-to-text transcription using Groq Whisper.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.middleware.session_auth import get_authenticated_session
from app.models.session import Session
from app.providers.groq import GroqProvider
from app.providers.factory import get_model_provider

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    session: Session = Depends(get_authenticated_session),
):
    """
    Transcribe audio recording to text using Whisper on Groq.
    Supports Telugu, Hindi, English, and other regional languages.
    """
    try:
        content = await file.read()
        provider = get_model_provider()

        if isinstance(provider, GroqProvider):
            groq_provider = provider
        else:
            groq_provider = GroqProvider()

        lang_code = language or session.language or "en"
        text = await groq_provider.transcribe_audio(
            audio_bytes=content,
            filename=file.filename or "recording.webm",
            language=lang_code,
        )
        return {"text": text, "language": lang_code}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech transcription failed: {str(e)}",
        )
