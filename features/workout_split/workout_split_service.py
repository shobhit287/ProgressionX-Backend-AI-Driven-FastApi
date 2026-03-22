from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .workout_split_repository import WorkoutSplitRepository
from .workout_split_enum import DayEnum


class WorkoutSplitService:
    def __init__(self, db: AsyncSession):
        self.workout_split_repository = WorkoutSplitRepository(db)

    async def create(self, user_id: UUID, payload: dict):
        payload["user_id"] = user_id
        split = await self.workout_split_repository.create(payload)
        return split

    async def get_all(self, user_id: UUID):
        return await self.workout_split_repository.get_all_by_user(user_id)

    async def get_today(self, user_id: UUID):
        today = datetime.now().strftime("%A").lower()
        day_enum = DayEnum(today)
        return await self.workout_split_repository.get_by_user_and_day(user_id, day_enum)

    async def get_by_id(self, split_id: UUID, user_id: UUID):
        return await self.workout_split_repository.get_by_id(split_id, user_id)

    async def update(self, split_id: UUID, user_id: UUID, payload: dict):
        split = await self.workout_split_repository.get_by_id(split_id, user_id)
        updated_split = await self.workout_split_repository.update(split, payload)
        return updated_split

    async def delete(self, split_id: UUID, user_id: UUID):
        split = await self.workout_split_repository.get_by_id(split_id, user_id)
        await self.workout_split_repository.delete(split)
