"""API router aggregation — mounts all v1 route modules."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.notes import router as notes_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.usage import router as usage_router
from app.api.v1.websocket import router as websocket_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(reminders_router)
api_router.include_router(notes_router)
api_router.include_router(usage_router)
api_router.include_router(websocket_router)
