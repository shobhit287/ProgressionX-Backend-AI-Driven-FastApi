from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .diet_model import DietPlan


class DietRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user(self, user_id: UUID) -> DietPlan | None:
        result = await self.db.execute(
            select(DietPlan).where(DietPlan.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: UUID, content: str) -> DietPlan:
        existing = await self.get_by_user(user_id)
        if existing:
            existing.content = content
            await self.db.flush()
            return existing
        plan = DietPlan(user_id=user_id, content=content)
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def delete(self, plan: DietPlan) -> None:
        await self.db.delete(plan)
        await self.db.flush()
