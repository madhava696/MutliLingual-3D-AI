"""Health check endpoint."""

from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check — no auth required."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "name": settings.APP_NAME,
    }
