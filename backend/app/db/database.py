"""
Async database engine and session factory.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,  #Represents a session to execute the db operations async'ly
    async_sessionmaker,  #create a resuable factory for creating sessions
    create_async_engine,  #creates the db engine async'ly
)
from sqlalchemy.orm import DeclarativeBase  #provides base class for defining ORM models

from app.config import get_settings

engine = None
async_session_factory = None


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


async def init_db():
    """Initialize the async database engine and session factory."""
    global engine, async_session_factory
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG, #Logs SQL statements when debug mode is enabled.
        pool_size=5, #keep up to 5 conn's in standard conn pool
        max_overflow=10, # allows up to additional 10 conn beyond mentioned size
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Ensure tables exist
    import app.models  # noqa: F401
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[DB Init Warning] Table auto-creation notice: {e}")


async def close_db():
    """Close the database engine."""
    global engine
    if engine:
        await engine.dispose()


async def get_db() -> AsyncSession:
    """Dependency that provides an async database session."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
