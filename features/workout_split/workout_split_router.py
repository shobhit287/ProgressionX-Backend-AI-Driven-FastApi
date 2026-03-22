from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from core.depends import get_db, current_user
from .workout_split_schema import (
    CreateWorkoutSplitSchema,
    UpdateWorkoutSplitSchema,
    ResponseWorkoutSplitSchema,
)
from .workout_split_service import WorkoutSplitService


router = APIRouter(prefix="/splits", tags=["Workout Splits"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseWorkoutSplitSchema,
)
async def create_split(
    data: CreateWorkoutSplitSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSplitService(db)
    split = await service.create(user.id, data.model_dump())
    await db.commit()
    await db.refresh(split)
    return split


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[ResponseWorkoutSplitSchema],
)
async def get_all_splits(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSplitService(db)
    splits = await service.get_all(user.id)
    return splits


@router.get(
    "/today",
    status_code=status.HTTP_200_OK,
    response_model=ResponseWorkoutSplitSchema | None,
)
async def get_today_split(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSplitService(db)
    split = await service.get_today(user.id)
    return split


@router.get(
    "/{split_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseWorkoutSplitSchema,
)
async def get_split(
    split_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSplitService(db)
    split = await service.get_by_id(split_id, user.id)
    return split


@router.patch(
    "/{split_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseWorkoutSplitSchema,
)
async def update_split(
    split_id: UUID,
    data: UpdateWorkoutSplitSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSplitService(db)
    split = await service.update(split_id, user.id, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(split)
    return split


@router.delete(
    "/{split_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_split(
    split_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkoutSplitService(db)
    await service.delete(split_id, user.id)
    await db.commit()
    return None
