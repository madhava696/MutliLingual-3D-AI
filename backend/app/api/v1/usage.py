"""
Usage API endpoint.
Returns privacy-safe aggregated cost/usage data for a session.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.middleware.session_auth import get_authenticated_session
from app.models.session import Session
from app.models.usage_log import UsageLog
from app.schemas.usage import UsageByProvider, UsageByTask, UsageSummaryResponse

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageSummaryResponse)
async def get_usage(
    session_id: uuid.UUID = Query(...),
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated usage and cost data for a session."""
    if session_id != session.id:
        raise HTTPException(status_code=403, detail="Session mismatch")

    # By provider
    provider_result = await db.execute(
        select(
            UsageLog.provider,
            func.coalesce(func.sum(UsageLog.estimated_cost_usd), 0).label("total_cost"),
            func.count().label("total_requests"),
        )
        .where(UsageLog.session_id == session_id)
        .group_by(UsageLog.provider)
    )
    by_provider = [
        UsageByProvider(
            provider=row.provider,
            total_cost_usd=float(row.total_cost),
            total_requests=row.total_requests,
        )
        for row in provider_result.all()
    ]

    # By task type
    task_result = await db.execute(
        select(
            UsageLog.task_type,
            func.coalesce(func.sum(UsageLog.estimated_cost_usd), 0).label("total_cost"),
            func.count().label("total_requests"),
        )
        .where(UsageLog.session_id == session_id)
        .group_by(UsageLog.task_type)
    )
    by_task = [
        UsageByTask(
            task_type=row.task_type,
            total_cost_usd=float(row.total_cost),
            total_requests=row.total_requests,
        )
        for row in task_result.all()
    ]

    total_cost = sum(p.total_cost_usd for p in by_provider)
    total_requests = sum(p.total_requests for p in by_provider)

    return UsageSummaryResponse(
        total_cost_usd=total_cost,
        total_requests=total_requests,
        by_provider=by_provider,
        by_task=by_task,
    )
