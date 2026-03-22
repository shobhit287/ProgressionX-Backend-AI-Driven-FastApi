from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from core.exception_handlers import BaseDomainError
from .exercise_set_model import ExerciseSet


class ExerciseSetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> ExerciseSet:
        exercise_set = ExerciseSet(**data)
        self.db.add(exercise_set)
        await self.db.flush()
        return exercise_set

    async def get_by_id(self, set_id: UUID) -> ExerciseSet:
        result = await self.db.execute(
            select(ExerciseSet).where(ExerciseSet.id == set_id)
        )
        exercise_set = result.scalar_one_or_none()

        if not exercise_set:
            raise BaseDomainError("Exercise set not found", 404)

        return exercise_set

    async def get_all_by_session_exercise(self, session_exercise_id: UUID) -> list[ExerciseSet]:
        result = await self.db.execute(
            select(ExerciseSet)
            .where(ExerciseSet.session_exercise_id == session_exercise_id)
            .order_by(ExerciseSet.set_number)
        )
        return result.scalars().all()

    async def get_next_set_number(self, session_exercise_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(ExerciseSet.set_number)).where(
                ExerciseSet.session_exercise_id == session_exercise_id
            )
        )
        max_number = result.scalar()
        return (max_number or 0) + 1

    async def update(self, exercise_set: ExerciseSet, data: dict) -> ExerciseSet:
        for field, value in data.items():
            setattr(exercise_set, field, value)

        await self.db.flush()
        return exercise_set

    async def delete(self, exercise_set: ExerciseSet) -> None:
        await self.db.delete(exercise_set)
        await self.db.flush()

    async def renumber_sets(self, session_exercise_id: UUID) -> None:
        sets = await self.get_all_by_session_exercise(session_exercise_id)
        for i, exercise_set in enumerate(sets, start=1):
            exercise_set.set_number = i
        await self.db.flush()
