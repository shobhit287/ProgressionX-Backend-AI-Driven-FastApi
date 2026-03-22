from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date
from typing import Optional

from core.depends import get_db, current_user
from core.pagination import PaginatedResponse
from .weight_log_schema import (
    CreateWeightLogSchema,
    ResponseWeightLogSchema,
    WeightAnalyticsSchema,
)
from .weight_log_service import WeightLogService


router = APIRouter(prefix="/weight-logs", tags=["Weight Logs"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseWeightLogSchema,
)
async def create_weight_log(
    data: CreateWeightLogSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WeightLogService(db)
    log = await service.create(user.id, data.model_dump())
    await db.commit()
    await db.refresh(log)
    return log


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedResponse[ResponseWeightLogSchema],
)
async def get_weight_logs(
    from_date: Optional[date] = Query(None, alias="fromDate"),
    to_date: Optional[date] = Query(None, alias="toDate"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WeightLogService(db)
    result = await service.get_all(user.id, from_date, to_date, page, page_size)
    return result


@router.get(
    "/analytics",
    status_code=status.HTTP_200_OK,
    response_model=WeightAnalyticsSchema,
)
async def get_weight_analytics(
    from_date: Optional[date] = Query(None, alias="fromDate"),
    to_date: Optional[date] = Query(None, alias="toDate"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WeightLogService(db)
    result = await service.get_analytics(user.id, from_date, to_date)
    return result


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_weight_log(
    log_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WeightLogService(db)
    await service.delete(log_id, user.id)
    await db.commit()
    return None
