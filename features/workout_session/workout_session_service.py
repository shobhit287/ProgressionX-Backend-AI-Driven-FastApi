from datetime import datetime, timezone, date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.exception_handlers import BaseDomainError
from features.split_exercise.split_exercise_model import SplitExercise
from .workout_session_repository import WorkoutSessionRepository
from .workout_session_enum import SessionStatusEnum
from .session_exercise_model import SessionExercise


class WorkoutSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = WorkoutSessionRepository(db)

    async def start_session(self, user_id: UUID, split_id: UUID):
        active = await self.repository.get_active(user_id)
        if active:
            # Auto-complete any existing active session so a new one can start
            started = active.started_at.replace(tzinfo=timezone.utc) if active.started_at.tzinfo is None else active.started_at
            now = datetime.now(timezone.utc)
            duration = int((now - started).total_seconds())
            is_previous_day = started.date() < now.date()
            await self.repository.update(active, {
                "status": SessionStatusEnum.COMPLETED,
                "completed_at": now,
                "duration_seconds": duration,
                "notes": "Auto-completed (previous session replaced by new start)" if is_previous_day else "Auto-completed (new session started)",
            })

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
        session = await self.repository.get_active(user_id)
        if not session:
            return None

        # Auto-complete sessions from a previous calendar day
        started = session.started_at.replace(tzinfo=timezone.utc) if session.started_at.tzinfo is None else session.started_at
        if started.date() < datetime.now(timezone.utc).date():
            now = datetime.now(timezone.utc)
            duration = int((now - started).total_seconds())
            await self.repository.update(session, {
                "status": SessionStatusEnum.COMPLETED,
                "completed_at": now,
                "duration_seconds": duration,
                "notes": "Auto-completed (session from previous day)",
            })
            await self.db.commit()
            return None

        # Sync new exercises added to the split after session started
        synced = await self._sync_split_exercises(session)

        # Re-fetch with eager loading if new exercises were added,
        # otherwise the newly appended SessionExercise objects lack loaded 'sets'
        if synced:
            return await self.repository.get_by_id_with_details(session.id, session.user_id)
        return session

    async def get_by_id(self, session_id: UUID, user_id: UUID):
        session = await self.repository.get_by_id_with_details(session_id, user_id)
        if session and session.status == SessionStatusEnum.IN_PROGRESS:
            synced = await self._sync_split_exercises(session)
            if synced:
                return await self.repository.get_by_id_with_details(session_id, user_id)
        return session

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

    async def _sync_split_exercises(self, session) -> bool:
        """Add any exercises that were added to the split after the session started.
        Returns True if new exercises were added."""
        result = await self.db.execute(
            select(SplitExercise)
            .where(SplitExercise.split_id == session.split_id)
            .order_by(SplitExercise.display_order)
        )
        current_split_exercises = result.scalars().all()

        existing_split_exercise_ids = {
            ex.split_exercise_id for ex in session.exercises if ex.split_exercise_id
        }

        new_exercises = [
            ex for ex in current_split_exercises
            if ex.id not in existing_split_exercise_ids
        ]

        if not new_exercises:
            return False

        max_order = max((ex.display_order for ex in session.exercises), default=0)
        for ex in new_exercises:
            max_order += 1
            session_exercise = SessionExercise(
                session_id=session.id,
                split_exercise_id=ex.id,
                exercise_name=ex.name,
                display_order=max_order,
                exercise_type=ex.exercise_type,
                superset_group=ex.superset_group,
            )
            self.db.add(session_exercise)

        await self.db.flush()
        return True
