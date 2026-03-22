from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date
from typing import Optional

from core.depends import get_db, current_user
from .analytics_schema import (
    SessionAnalyticsResponse,
    ExerciseAnalyticsResponse,
    DashboardSummaryResponse,
)
from .analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
    response_model=SessionAnalyticsResponse,
)
async def get_session_analytics(
    split_id: Optional[UUID] = Query(None, alias="splitId"),
    from_date: Optional[date] = Query(None, alias="fromDate"),
    to_date: Optional[date] = Query(None, alias="toDate"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    result = await service.get_session_analytics(user.id, split_id, from_date, to_date)
    return result


@router.get(
    "/exercises/{exercise_name}",
    status_code=status.HTTP_200_OK,
    response_model=ExerciseAnalyticsResponse,
)
async def get_exercise_analytics(
    exercise_name: str,
    from_date: Optional[date] = Query(None, alias="fromDate"),
    to_date: Optional[date] = Query(None, alias="toDate"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    result = await service.get_exercise_analytics(user.id, exercise_name, from_date, to_date)
    return result


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    response_model=DashboardSummaryResponse,
)
async def get_dashboard_summary(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    result = await service.get_dashboard_summary(user.id)
    return result
