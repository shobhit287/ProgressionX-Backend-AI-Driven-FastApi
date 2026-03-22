from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from core.exception_handlers import BaseDomainError
from .split_exercise_model import SplitExercise


class SplitExerciseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, exercise_data: dict) -> SplitExercise:
        exercise = SplitExercise(**exercise_data)
        self.db.add(exercise)
        await self.db.flush()
        return exercise

    async def get_by_id(self, exercise_id: UUID) -> SplitExercise:
        result = await self.db.execute(
            select(SplitExercise).where(SplitExercise.id == exercise_id)
        )
        exercise = result.scalar_one_or_none()

        if not exercise:
            raise BaseDomainError("Exercise not found", 404)

        return exercise

    async def get_all_by_split(self, split_id: UUID) -> list[SplitExercise]:
        result = await self.db.execute(
            select(SplitExercise)
            .where(SplitExercise.split_id == split_id)
            .order_by(SplitExercise.display_order)
        )
        return result.scalars().all()

    async def get_max_display_order(self, split_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(SplitExercise.display_order), 0)).where(
                SplitExercise.split_id == split_id
            )
        )
        return result.scalar()

    async def update(self, exercise: SplitExercise, data: dict) -> SplitExercise:
        for field, value in data.items():
            setattr(exercise, field, value)

        await self.db.flush()
        return exercise

    async def delete(self, exercise: SplitExercise) -> None:
        await self.db.delete(exercise)
        await self.db.flush()

    async def bulk_update_order(self, order_map: list[dict]) -> None:
        for item in order_map:
            result = await self.db.execute(
                select(SplitExercise).where(SplitExercise.id == item["id"])
            )
            exercise = result.scalar_one_or_none()
            if exercise:
                exercise.display_order = item["display_order"]

        await self.db.flush()
