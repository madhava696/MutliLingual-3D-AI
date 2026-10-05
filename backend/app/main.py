"""
FastAPI application factory.
Entry point for the backend server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import init_db, close_db
from app.api.router import api_router
from app.middleware.error_handler import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    settings = get_settings()

    # Startup
    await init_db()
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} starting...")

    yield

    # Shutdown
    await close_db()
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="India-first Multilingual 3D AI Companion API",
        lifespan=lifespan,
    )

    # CORS — restrict to frontend origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    register_error_handlers(app)

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
