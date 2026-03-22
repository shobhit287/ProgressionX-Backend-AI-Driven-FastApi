from uuid import UUID
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from .weight_log_repository import WeightLogRepository


class WeightLogService:
    def __init__(self, db: AsyncSession):
        self.weight_log_repository = WeightLogRepository(db)

    async def create(self, user_id: UUID, payload: dict):
        payload["user_id"] = user_id
        if payload.get("logged_at") is None:
            payload["logged_at"] = date.today()
        log = await self.weight_log_repository.create(payload)
        return log

    async def get_all(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        logs, total = await self.weight_log_repository.get_all(
            user_id, from_date, to_date, page, page_size
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "items": logs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_analytics(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ):
        logs = await self.weight_log_repository.get_analytics_data(
            user_id, from_date, to_date
        )

        if not logs:
            return {
                "weekly_averages": [],
                "rate_of_change": 0.0,
                "total_change": 0.0,
                "entries": 0,
            }

        # Compute weekly averages
        weekly_data = defaultdict(list)
        for log in logs:
            # ISO week: start on Monday
            week_start = log.logged_at - timedelta(days=log.logged_at.weekday())
            weekly_data[week_start].append(log.weight_kg)

        weekly_averages = []
        for week_start in sorted(weekly_data.keys()):
            weights = weekly_data[week_start]
            weekly_averages.append({
                "week_start": week_start,
                "average_weight": round(sum(weights) / len(weights), 2),
                "entries": len(weights),
            })

        # Rate of change (kg per week)
        total_change = 0.0
        rate_of_change = 0.0

        if len(logs) >= 2:
            first_weight = logs[0].weight_kg
            last_weight = logs[-1].weight_kg
            total_change = round(last_weight - first_weight, 2)

            days_span = (logs[-1].logged_at - logs[0].logged_at).days
            if days_span > 0:
                rate_of_change = round(total_change / (days_span / 7), 2)

        return {
            "weekly_averages": weekly_averages,
            "rate_of_change": rate_of_change,
            "total_change": total_change,
            "entries": len(logs),
        }

    async def delete(self, log_id: UUID, user_id: UUID):
        log = await self.weight_log_repository.get_by_id(log_id, user_id)
        await self.weight_log_repository.delete(log)
