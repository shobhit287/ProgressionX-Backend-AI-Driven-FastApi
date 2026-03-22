from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from datetime import date
from typing import Optional

from core.exception_handlers import BaseDomainError
from .weight_log_model import WeightLog


class WeightLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log_data: dict) -> WeightLog:
        try:
            log = WeightLog(**log_data)
            self.db.add(log)
            await self.db.flush()
            return log
        except IntegrityError:
            raise BaseDomainError("A weight log already exists for this date", 409)

    async def get_by_id(self, log_id: UUID, user_id: UUID) -> WeightLog:
        result = await self.db.execute(
            select(WeightLog).where(
                WeightLog.id == log_id,
                WeightLog.user_id == user_id,
            )
        )
        log = result.scalar_one_or_none()

        if not log:
            raise BaseDomainError("Weight log not found", 404)

        return log

    async def get_all(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WeightLog], int]:
        query = select(WeightLog).where(WeightLog.user_id == user_id)
        count_query = select(func.count()).select_from(WeightLog).where(WeightLog.user_id == user_id)

        if from_date:
            query = query.where(WeightLog.logged_at >= from_date)
            count_query = count_query.where(WeightLog.logged_at >= from_date)
        if to_date:
            query = query.where(WeightLog.logged_at <= to_date)
            count_query = count_query.where(WeightLog.logged_at <= to_date)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(WeightLog.logged_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        return logs, total

    async def delete(self, log: WeightLog) -> None:
        await self.db.delete(log)
        await self.db.flush()

    async def get_analytics_data(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[WeightLog]:
        query = select(WeightLog).where(WeightLog.user_id == user_id)

        if from_date:
            query = query.where(WeightLog.logged_at >= from_date)
        if to_date:
            query = query.where(WeightLog.logged_at <= to_date)

        query = query.order_by(WeightLog.logged_at.asc())

        result = await self.db.execute(query)
        return result.scalars().all()
