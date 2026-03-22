from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from core.exception_handlers import BaseDomainError
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_session.session_exercise_model import SessionExercise
from features.workout_session.workout_session_enum import SessionStatusEnum
from features.exercise_set.exercise_set_model import ExerciseSet
from .exercise_set_repository import ExerciseSetRepository


class ExerciseSetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ExerciseSetRepository(db)

    async def _verify_session_ownership(self, session_id: UUID, user_id: UUID) -> WorkoutSession:
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

    async def _verify_session_exercise(self, session_exercise_id: UUID, session_id: UUID) -> SessionExercise:
        result = await self.db.execute(
            select(SessionExercise).where(
                SessionExercise.id == session_exercise_id,
                SessionExercise.session_id == session_id,
            )
        )
        exercise = result.scalar_one_or_none()

        if not exercise:
            raise BaseDomainError("Session exercise not found", 404)

        return exercise

    async def add_set(
        self,
        session_id: UUID,
        session_exercise_id: UUID,
        user_id: UUID,
        data: dict,
    ):
        session = await self._verify_session_ownership(session_id, user_id)

        if session.status != SessionStatusEnum.IN_PROGRESS:
            raise BaseDomainError("Session is not in progress", 400)

        await self._verify_session_exercise(session_exercise_id, session_id)

        set_number = await self.repository.get_next_set_number(session_exercise_id)

        data["session_exercise_id"] = session_exercise_id
        data["set_number"] = set_number

        return await self.repository.create(data)

    async def update_set(self, set_id: UUID, session_id: UUID, user_id: UUID, data: dict):
        await self._verify_session_ownership(session_id, user_id)

        exercise_set = await self.repository.get_by_id(set_id)

        # Verify the set belongs to an exercise in this session
        await self._verify_session_exercise(exercise_set.session_exercise_id, session_id)

        return await self.repository.update(exercise_set, data)

    async def delete_set(self, set_id: UUID, session_id: UUID, user_id: UUID):
        await self._verify_session_ownership(session_id, user_id)

        exercise_set = await self.repository.get_by_id(set_id)

        await self._verify_session_exercise(exercise_set.session_exercise_id, session_id)

        session_exercise_id = exercise_set.session_exercise_id
        await self.repository.delete(exercise_set)
        await self.repository.renumber_sets(session_exercise_id)

    async def get_previous_sets(self, session_id: UUID, user_id: UUID) -> dict:
        """
        For the given session, find the most recent COMPLETED session with the
        same split_id and return a map: { exercise_name -> [sets] }
        """
        current = await self._verify_session_ownership(session_id, user_id)

        # Find the previous completed session for the same split
        result = await self.db.execute(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.exercises)
                .selectinload(SessionExercise.sets)
            )
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.split_id == current.split_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                WorkoutSession.id != session_id,
            )
            .order_by(desc(WorkoutSession.started_at))
            .limit(1)
        )
        prev_session = result.scalar_one_or_none()

        if not prev_session:
            return {}

        # Build map: exercise_name (lowered) -> list of sets sorted by set_number
        prev_map: dict[str, list[dict]] = {}
        for ex in prev_session.exercises:
            key = ex.exercise_name.lower()
            sets_data = sorted(
                [
                    {
                        "set_number": s.set_number,
                        "weight_kg": s.weight_kg,
                        "reps": s.reps,
                        "reps_in_reserve": s.reps_in_reserve,
                    }
                    for s in ex.sets
                ],
                key=lambda s: s["set_number"],
            )
            prev_map[key] = sets_data

        return prev_map
