"""
Shared test fixtures.

Uses an in-memory SQLite database with aiosqlite so tests can run
without Postgres or Redis.  Postgres-specific DDL (JSONB, gen_random_uuid,
server_default casts) is intercepted at compile time so SQLite can execute
the schema unchanged.
"""

import uuid
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import create_app
from app.models.note import Note
from app.models.reminder import Reminder
from app.models.session import Session
from app.models.usage_log import UsageLog

# ---------------------------------------------------------------------------
# In-memory async SQLite engine (no Postgres required)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.db import database
database.async_session_factory = TestSessionLocal


# ---------------------------------------------------------------------------
# Patch Postgres-specific DDL so SQLite can CREATE TABLE
# ---------------------------------------------------------------------------
@event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
def _patch_ddl_for_sqlite(conn, cursor, statement, parameters, context, executemany):
    """
    Rewrite Postgres-isms in DDL statements so SQLite can execute them:
      - gen_random_uuid()  → (lower(hex(randomblob(4)))||…)  — a SQLite UUID hack
      - JSONB columns      → TEXT
      - '{}'::jsonb         → '{}'
    """
    if not statement.strip().upper().startswith("CREATE"):
        return statement, parameters

    # Replace server_default: gen_random_uuid() → a SQLite expression
    sqlite_uuid = (
        "(lower(hex(randomblob(4)))||'-'||lower(hex(randomblob(2)))||'-4'"
        "||substr(lower(hex(randomblob(2))),2)||'-'"
        "||substr('89ab',abs(random())%4+1,1)"
        "||substr(lower(hex(randomblob(2))),2)||'-'"
        "||lower(hex(randomblob(6))))"
    )
    statement = statement.replace("gen_random_uuid()", sqlite_uuid)

    # Remove Postgres type casts  e.g.  DEFAULT '{}'::jsonb
    statement = re.sub(r"::jsonb", "", statement, flags=re.IGNORECASE)

    # Replace JSONB type with TEXT
    statement = re.sub(r"\bJSONB\b", "TEXT", statement, flags=re.IGNORECASE)

    # Replace UUID type with VARCHAR(36)
    statement = re.sub(r"\bUUID\b", "VARCHAR(36)", statement, flags=re.IGNORECASE)

    return statement, parameters


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    """Yield an async session bound to the test database."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _noop_lifespan(app):
    """No-op lifespan so tests don't start the real DB."""
    yield


@pytest.fixture
async def app():
    """Create a test-ready FastAPI application with dependency overrides."""
    application = create_app()
    application.router.lifespan_context = _noop_lifespan
    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest.fixture
async def client(app):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Helper: create a session directly in the DB (returns dict with useful data)
# ---------------------------------------------------------------------------

@pytest.fixture
async def create_test_session():
    """Factory fixture — call to create a session row and return metadata."""

    async def _create(*, language="en", private_mode=False):
        import secrets

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)

        async with TestSessionLocal() as db:
            session = Session(
                id=session_id,
                session_token=token,
                language=language,
                private_mode=private_mode,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(session)
            await db.commit()

        return {
            "session_id": session_id,
            "session_token": token,
            "language": language,
            "private_mode": private_mode,
        }

    return _create


# ---------------------------------------------------------------------------
# Helper: create a note directly in the DB
# ---------------------------------------------------------------------------

@pytest.fixture
async def create_test_note():
    """Factory fixture — create a note row tied to a session."""

    async def _create(session_id: uuid.UUID, *, title="Test Note", content="Body text", source_type=None):
        now = datetime.now(timezone.utc)
        note_id = uuid.uuid4()
        async with TestSessionLocal() as db:
            note = Note(
                id=note_id,
                session_id=session_id,
                title=title,
                content=content,
                language="en",
                source_type=source_type,
                created_at=now,
                updated_at=now,
            )
            db.add(note)
            await db.commit()
        return {"id": note_id, "session_id": session_id, "title": title, "content": content}

    return _create


# ---------------------------------------------------------------------------
# Helper: create a reminder directly in the DB
# ---------------------------------------------------------------------------

@pytest.fixture
async def create_test_reminder():
    """Factory fixture — create a reminder row tied to a session."""

    async def _create(
        session_id: uuid.UUID,
        *,
        title="Test Reminder",
        description=None,
        remind_at=None,
        status="pending",
    ):
        now = datetime.now(timezone.utc)
        reminder_id = uuid.uuid4()
        async with TestSessionLocal() as db:
            reminder = Reminder(
                id=reminder_id,
                session_id=session_id,
                title=title,
                description=description,
                remind_at=remind_at or (now + timedelta(hours=1)),
                status=status,
                language="en",
                created_at=now,
                updated_at=now,
            )
            db.add(reminder)
            await db.commit()
        return {
            "id": reminder_id,
            "session_id": session_id,
            "title": title,
            "description": description,
            "status": status,
        }

    return _create


# ---------------------------------------------------------------------------
# Helper: create a usage log directly in the DB
# ---------------------------------------------------------------------------

@pytest.fixture
async def create_test_usage_log():
    """Factory fixture — create a usage_log row tied to a session."""

    async def _create(
        session_id: uuid.UUID,
        *,
        provider="gemini",
        model="gemini-2.0-flash",
        task_type="chat",
        input_tokens=100,
        output_tokens=200,
        estimated_cost_usd=0.001,
        latency_ms=350,
        status="success",
    ):
        now = datetime.now(timezone.utc)
        log_id = uuid.uuid4()
        async with TestSessionLocal() as db:
            log = UsageLog(
                id=log_id,
                session_id=session_id,
                provider=provider,
                model=model,
                task_type=task_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=estimated_cost_usd,
                latency_ms=latency_ms,
                status=status,
                created_at=now,
            )
            db.add(log)
            await db.commit()
        return {"id": log_id, "session_id": session_id}

    return _create
