from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from uuid import UUID

from core.exception_handlers import BaseDomainError
from .workout_session_model import WorkoutSession
from .session_exercise_model import SessionExercise
from .workout_session_enum import SessionStatusEnum


class WorkoutSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> WorkoutSession:
        session = WorkoutSession(**data)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_id(self, session_id: UUID, user_id: UUID) -> WorkoutSession:
        result = await self.db.execute(
            select(WorkoutSession).where(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise BaseDomainError("Workout session not found", 404)

        return session

    async def get_by_id_with_details(self, session_id: UUID, user_id: UUID) -> WorkoutSession:
        result = await self.db.execute(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.exercises).selectinload(SessionExercise.sets)
            )
            .where(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise BaseDomainError("Workout session not found", 404)

        return session

    async def get_active(self, user_id: UUID) -> WorkoutSession | None:
        result = await self.db.execute(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.exercises).selectinload(SessionExercise.sets)
            )
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.IN_PROGRESS,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        user_id: UUID,
        filters: dict,
    ) -> tuple[list[WorkoutSession], int]:
        query = select(WorkoutSession).where(WorkoutSession.user_id == user_id)
        count_query = select(func.count()).select_from(WorkoutSession).where(
            WorkoutSession.user_id == user_id
        )

        if filters.get("split_id"):
            query = query.where(WorkoutSession.split_id == filters["split_id"])
            count_query = count_query.where(WorkoutSession.split_id == filters["split_id"])

        if filters.get("status"):
            query = query.where(WorkoutSession.status == filters["status"])
            count_query = count_query.where(WorkoutSession.status == filters["status"])

        if filters.get("from_date"):
            query = query.where(WorkoutSession.started_at >= filters["from_date"])
            count_query = count_query.where(WorkoutSession.started_at >= filters["from_date"])

        if filters.get("to_date"):
            query = query.where(WorkoutSession.started_at <= filters["to_date"])
            count_query = count_query.where(WorkoutSession.started_at <= filters["to_date"])

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        page = filters.get("page", 1)
        page_size = filters.get("page_size", 20)
        offset = (page - 1) * page_size

        query = query.order_by(desc(WorkoutSession.started_at)).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        return sessions, total

    async def update(self, session: WorkoutSession, data: dict) -> WorkoutSession:
        for field, value in data.items():
            setattr(session, field, value)

        await self.db.flush()
        return session

    async def delete(self, session: WorkoutSession) -> None:
        await self.db.delete(session)
        await self.db.flush()

    async def create_session_exercises(
        self, session_id: UUID, exercises_data: list[dict]
    ) -> list[SessionExercise]:
        exercises = []
        for data in exercises_data:
            data["session_id"] = session_id
            exercise = SessionExercise(**data)
            self.db.add(exercise)
            exercises.append(exercise)

        await self.db.flush()
        return exercises
