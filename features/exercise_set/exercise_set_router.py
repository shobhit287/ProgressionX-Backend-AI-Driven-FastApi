from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from core.depends import get_db, current_user
from .exercise_set_schema import (
    CreateExerciseSetSchema,
    UpdateExerciseSetSchema,
    ResponseExerciseSetSchema,
)
from .exercise_set_service import ExerciseSetService


router = APIRouter(prefix="/sessions", tags=["Exercise Sets"])


@router.get(
    "/{session_id}/previous-sets",
    status_code=status.HTTP_200_OK,
)
async def get_previous_sets(
    session_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseSetService(db)
    return await service.get_previous_sets(session_id, user.id)


@router.post(
    "/{session_id}/exercises/{exercise_id}/sets",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseExerciseSetSchema,
)
async def add_set(
    session_id: UUID,
    exercise_id: UUID,
    data: CreateExerciseSetSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseSetService(db)
    exercise_set = await service.add_set(
        session_id, exercise_id, user.id, data.model_dump()
    )
    await db.commit()
    await db.refresh(exercise_set)
    return exercise_set


@router.patch(
    "/{session_id}/sets/{set_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseExerciseSetSchema,
)
async def update_set(
    session_id: UUID,
    set_id: UUID,
    data: UpdateExerciseSetSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseSetService(db)
    exercise_set = await service.update_set(
        set_id, session_id, user.id, data.model_dump(exclude_unset=True)
    )
    await db.commit()
    await db.refresh(exercise_set)
    return exercise_set


@router.delete(
    "/{session_id}/sets/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_set(
    session_id: UUID,
    set_id: UUID,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExerciseSetService(db)
    await service.delete_set(set_id, session_id, user.id)
    await db.commit()
    return None
