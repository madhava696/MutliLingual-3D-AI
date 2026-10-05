"""
Session Data Deletion Service.
Comprehensive cleanup: PostgreSQL + Redis + filesystem + temp files.
Does NOT rely solely on database cascade.
"""

import os
import uuid
import glob
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.uploaded_file import UploadedFile
from app.models.usage_log import UsageLog

logger = logging.getLogger(__name__)


class DeletionReport:
    """Report of what was deleted."""
    def __init__(self):
        self.db_records_deleted = False
        self.redis_keys_deleted = 0
        self.files_removed: list[str] = []
        self.temp_files_removed: list[str] = []
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "db_records_deleted": self.db_records_deleted,
            "redis_keys_deleted": self.redis_keys_deleted,
            "files_removed": len(self.files_removed),
            "temp_files_removed": len(self.temp_files_removed),
            "errors": self.errors,
        }


async def delete_session_data(
    db: AsyncSession,
    session: Session,
    redis_client=None,
) -> DeletionReport:
    """
    Comprehensive session data deletion:
    1. Get uploaded file paths BEFORE deleting DB records
    2. Delete filesystem files
    3. Delete Redis session context
    4. Clean up temp audio/transcript files
    5. Nullify session_id in usage_logs (retain anonymized metrics)
    6. Delete DB records (cascade: reminders, notes, uploaded_files)
    """
    report = DeletionReport()
    session_id = session.id

    # 1. Get file paths before DB cascade
    file_result = await db.execute(
        select(UploadedFile.storage_path).where(
            UploadedFile.session_id == session_id
        )
    )
    file_paths = list(file_result.scalars().all())

    # 2. Delete filesystem files
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                report.files_removed.append(path)
        except OSError as e:
            report.errors.append(f"Failed to delete file {path}: {e}")
            logger.error(f"Failed to delete file {path}: {e}")

    # 3. Delete Redis session context
    if redis_client:
        try:
            pattern = f"session:{session_id}:*"
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                report.redis_keys_deleted = await redis_client.delete(*keys)
        except Exception as e:
            report.errors.append(f"Redis cleanup error: {e}")
            logger.error(f"Redis cleanup error for session {session_id}: {e}")

    # 4. Clean up temp files (audio, transcripts)
    temp_patterns = [
        f"./temp/audio_{session_id}_*",
        f"./temp/transcript_{session_id}_*",
    ]
    for pattern in temp_patterns:
        for temp_file in glob.glob(pattern):
            try:
                os.remove(temp_file)
                report.temp_files_removed.append(temp_file)
            except OSError as e:
                report.errors.append(f"Failed to delete temp file {temp_file}: {e}")

    # 5. Nullify session_id in usage_logs (retain anonymized metrics)
    await db.execute(
        update(UsageLog)
        .where(UsageLog.session_id == session_id)
        .values(session_id=None)
    )

    # 6. Delete session from DB (cascade: reminders, notes, uploaded_files)
    await db.delete(session)
    await db.flush()
    report.db_records_deleted = True

    logger.info(
        f"Session {session_id} deleted: "
        f"{len(report.files_removed)} files, "
        f"{report.redis_keys_deleted} redis keys, "
        f"{len(report.temp_files_removed)} temp files"
    )

    return report
