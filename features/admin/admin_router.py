from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db, require_superadmin
from .admin_schema import (
    AdminDashboardResponse,
    ActiveHoursResponse,
    LlmUsageResponse,
    AdminUsersResponse,
)
from .admin_service import AdminService


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    response_model=AdminDashboardResponse,
)
async def admin_dashboard(
    user=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_dashboard()


@router.get(
    "/active-hours",
    status_code=status.HTTP_200_OK,
    response_model=ActiveHoursResponse,
)
async def admin_active_hours(
    days: int = Query(30, ge=7, le=90),
    user=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_active_hours(days=days)


@router.get(
    "/llm-usage",
    status_code=status.HTTP_200_OK,
    response_model=LlmUsageResponse,
)
async def admin_llm_usage(
    days: int = Query(30, ge=7, le=90),
    user=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_llm_usage(days=days)


@router.get(
    "/users",
    status_code=status.HTTP_200_OK,
    response_model=AdminUsersResponse,
)
async def admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    search: str = Query(None),
    user=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_users(page=page, page_size=page_size, search=search)
