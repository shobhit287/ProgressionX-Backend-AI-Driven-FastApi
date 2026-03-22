from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from core.exception_handlers import BaseDomainError
from .workout_split_model import WorkoutSplit
from .workout_split_enum import DayEnum


class WorkoutSplitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, split_data: dict) -> WorkoutSplit:
        try:
            split = WorkoutSplit(**split_data)
            self.db.add(split)
            await self.db.flush()
            return split
        except IntegrityError:
            raise BaseDomainError("A workout split already exists for this day", 409)

    async def get_by_id(self, split_id: UUID, user_id: UUID) -> WorkoutSplit:
        result = await self.db.execute(
            select(WorkoutSplit).where(
                WorkoutSplit.id == split_id,
                WorkoutSplit.user_id == user_id,
            )
        )
        split = result.scalar_one_or_none()

        if not split:
            raise BaseDomainError("Workout split not found", 404)

        return split

    async def get_all_by_user(self, user_id: UUID) -> list[WorkoutSplit]:
        result = await self.db.execute(
            select(WorkoutSplit).where(WorkoutSplit.user_id == user_id)
        )
        return result.scalars().all()

    async def get_by_user_and_day(self, user_id: UUID, day: DayEnum) -> WorkoutSplit | None:
        result = await self.db.execute(
            select(WorkoutSplit).where(
                WorkoutSplit.user_id == user_id,
                WorkoutSplit.day == day,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, split: WorkoutSplit, data: dict) -> WorkoutSplit:
        for field, value in data.items():
            setattr(split, field, value)

        await self.db.flush()
        return split

    async def delete(self, split: WorkoutSplit) -> None:
        await self.db.delete(split)
        await self.db.flush()
