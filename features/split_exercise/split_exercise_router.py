from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from core.depends import get_db, current_user
from .split_exercise_schema import (
    CreateSplitExerciseSchema,
    UpdateSplitExerciseSchema,
    ReorderSchema,
    ResponseSplitExerciseSchema,
)
from .split_exercise_service import SplitExerciseService


router = APIRouter(prefix="/splits/{split_id}/exercises", tags=["Split Exercises"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSplitExerciseSchema,
)
async def create_exercise(
    split_id: UUID,
    data: CreateSplitExerciseSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SplitExerciseService(db)
    exercise = await service.create(split_id, user.id, data.model_dump())
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[ResponseSplitExerciseSchema],
)
async def get_all_exercises(
    split_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SplitExerciseService(db)
    exercises = await service.get_all_by_split(split_id, user.id)
    return exercises


@router.patch(
    "/reorder",
    status_code=status.HTTP_200_OK,
    response_model=list[ResponseSplitExerciseSchema],
)
async def reorder_exercises(
    split_id: UUID,
    data: ReorderSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SplitExerciseService(db)
    order_items = [
        {"id": item.id, "display_order": item.display_order}
        for item in data.exercises
    ]
    exercises = await service.reorder(split_id, user.id, order_items)
    await db.commit()
    return exercises


@router.patch(
    "/{exercise_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSplitExerciseSchema,
)
async def update_exercise(
    split_id: UUID,
    exercise_id: UUID,
    data: UpdateSplitExerciseSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SplitExerciseService(db)
    exercise = await service.update(split_id, exercise_id, user.id, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_exercise(
    split_id: UUID,
    exercise_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SplitExerciseService(db)
    await service.delete(split_id, exercise_id, user.id)
    await db.commit()
    return None
