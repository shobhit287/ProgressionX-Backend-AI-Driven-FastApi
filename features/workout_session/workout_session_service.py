from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.exception_handlers import BaseDomainError
from features.split_exercise.split_exercise_model import SplitExercise
from .workout_session_repository import WorkoutSessionRepository
from .workout_session_enum import SessionStatusEnum


class WorkoutSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = WorkoutSessionRepository(db)

    async def start_session(self, user_id: UUID, split_id: UUID):
        active = await self.repository.get_active(user_id)
        if active:
            raise BaseDomainError("An active workout session already exists", 409)

        session = await self.repository.create({
            "user_id": user_id,
            "split_id": split_id,
            "status": SessionStatusEnum.IN_PROGRESS,
        })

        result = await self.db.execute(
            select(SplitExercise)
            .where(SplitExercise.split_id == split_id)
            .order_by(SplitExercise.display_order)
        )
        split_exercises = result.scalars().all()

        exercises_data = [
            {
                "split_exercise_id": ex.id,
                "exercise_name": ex.name,
                "display_order": ex.display_order,
                "exercise_type": ex.exercise_type,
                "superset_group": ex.superset_group,
            }
            for ex in split_exercises
        ]

        await self.repository.create_session_exercises(session.id, exercises_data)

        return await self.repository.get_by_id_with_details(session.id, user_id)

    async def get_active(self, user_id: UUID):
        return await self.repository.get_active(user_id)

    async def get_by_id(self, session_id: UUID, user_id: UUID):
        return await self.repository.get_by_id_with_details(session_id, user_id)

    async def get_all(self, user_id: UUID, filters: dict):
        sessions, total = await self.repository.get_all(user_id, filters)
        return sessions, total

    async def complete_session(self, session_id: UUID, user_id: UUID, notes: str | None = None):
        session = await self.repository.get_by_id(session_id, user_id)

        if session.status != SessionStatusEnum.IN_PROGRESS:
            raise BaseDomainError("Session is not in progress", 400)

        now = datetime.now(timezone.utc)
        duration = int((now - session.started_at.replace(tzinfo=timezone.utc)).total_seconds()) if session.started_at else None

        update_data = {
            "status": SessionStatusEnum.COMPLETED,
            "completed_at": now,
            "duration_seconds": duration,
        }
        if notes is not None:
            update_data["notes"] = notes

        return await self.repository.update(session, update_data)

    async def abandon_session(self, session_id: UUID, user_id: UUID):
        session = await self.repository.get_by_id(session_id, user_id)

        if session.status != SessionStatusEnum.IN_PROGRESS:
            raise BaseDomainError("Session is not in progress", 400)

        now = datetime.now(timezone.utc)
        duration = int((now - session.started_at.replace(tzinfo=timezone.utc)).total_seconds()) if session.started_at else None

        return await self.repository.update(session, {
            "status": SessionStatusEnum.ABANDONED,
            "completed_at": now,
            "duration_seconds": duration,
        })

    async def delete_session(self, session_id: UUID, user_id: UUID):
        session = await self.repository.get_by_id(session_id, user_id)
        await self.repository.delete(session)
