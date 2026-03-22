from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from datetime import date

from core.depends import get_db, current_user
from .workout_session_schema import (
    StartSessionSchema,
    CompleteSessionSchema,
    ResponseSessionDetailSchema,
    ResponseSessionSchema,
    PaginatedSessionsSchema,
)
from .workout_session_enum import SessionStatusEnum
from .workout_session_service import WorkoutSessionService


router = APIRouter(prefix="/sessions", tags=["Workout Sessions"])


@router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSessionDetailSchema,
)
async def start_session(
    data: StartSessionSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSessionService(db)
    session = await service.start_session(user.id, data.split_id)
    await db.commit()
    await db.refresh(session)
    return session


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedSessionsSchema,
)
async def list_sessions(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
    split_id: Optional[UUID] = Query(None, alias="splitId"),
    from_date: Optional[date] = Query(None, alias="fromDate"),
    to_date: Optional[date] = Query(None, alias="toDate"),
    session_status: Optional[SessionStatusEnum] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
):
    service = WorkoutSessionService(db)
    filters = {
        "split_id": split_id,
        "from_date": from_date,
        "to_date": to_date,
        "status": session_status,
        "page": page,
        "page_size": page_size,
    }
    sessions, total = await service.get_all(user.id, filters)
    return PaginatedSessionsSchema(
        items=sessions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSessionDetailSchema | None,
)
async def get_active_session(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSessionService(db)
    session = await service.get_active(user.id)
    return session


@router.get(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSessionDetailSchema,
)
async def get_session(
    session_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSessionService(db)
    session = await service.get_by_id(session_id, user.id)
    return session


@router.patch(
    "/{session_id}/complete",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSessionSchema,
)
async def complete_session(
    session_id: UUID,
    data: CompleteSessionSchema = None,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSessionService(db)
    notes = data.notes if data else None
    session = await service.complete_session(session_id, user.id, notes)
    await db.commit()
    await db.refresh(session)
    return session


@router.patch(
    "/{session_id}/abandon",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSessionSchema,
)
async def abandon_session(
    session_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSessionService(db)
    session = await service.abandon_session(session_id, user.id)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSessionService(db)
    await service.delete_session(session_id, user.id)
    await db.commit()
    return None
