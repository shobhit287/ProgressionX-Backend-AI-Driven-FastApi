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

        # Allow adding sets to IN_PROGRESS sessions (live workout) AND to
        # COMPLETED sessions (backfill / editing a past session the user
        # forgot to log). ABANDONED stays locked — those represent an
        # explicit "I'm not doing this one" and shouldn't accept new sets.
        if session.status not in (
            SessionStatusEnum.IN_PROGRESS,
            SessionStatusEnum.COMPLETED,
        ):
            raise BaseDomainError("Session cannot accept new sets", 400)

        await self._verify_session_exercise(session_exercise_id, session_id)

        set_number = await self.repository.get_next_set_number(session_exercise_id)

        data["session_exercise_id"] = session_exercise_id
        data["set_number"] = set_number

        # Auto-link dropsets to their top set. If the client didn't send
        # parent_set_id and this is flagged as a dropset, walk back through
        # this exercise's sets to find the nearest non-dropset top set.
        if data.get("is_dropset") and not data.get("parent_set_id"):
            existing = await self.repository.get_all_by_session_exercise(
                session_exercise_id
            )
            top_set_id = None
            for prior in reversed(existing):
                if not prior.is_dropset:
                    top_set_id = prior.id
                    break
                if prior.parent_set_id is not None:
                    top_set_id = prior.parent_set_id
                    break
            if top_set_id is not None:
                data["parent_set_id"] = top_set_id

        # Validate parent_set_id if supplied: must be a set on the same
        # session_exercise (prevents cross-exercise linking).
        if data.get("parent_set_id"):
            parent = await self.repository.get_by_id(data["parent_set_id"])
            if parent.session_exercise_id != session_exercise_id:
                raise BaseDomainError(
                    "parent_set_id must reference a set on the same exercise", 400
                )

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
        For the given session, find the most recent COMPLETED session for
        the same split that actually has logged sets, and return a map:
        { exercise_name -> [sets] }.

        Empty completed sessions (auto-completed when a user started a new
        session without logging anything in the prior one) and abandoned /
        missed sessions are skipped so the PREV hint on each set always
        points at the last session the user actually trained — matching the
        Last Session panel.
        """
        current = await self._verify_session_ownership(session_id, user_id)

        # Fetch the 10 most recent completed sessions and pick the first one
        # that actually has logged sets. Matches get_previous_completed so
        # the panel header and the inline PREV hints always point at the
        # same prior session. Doing the empty-session filter in Python
        # avoids a SQL subquery whose autocorrelation broke this endpoint
        # in production.
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
            .limit(10)
        )
        prev_session = None
        for candidate in result.scalars().all():
            if any(ex.sets for ex in candidate.exercises):
                prev_session = candidate
                break

        if not prev_session:
            return {}

        # Build map: exercise_name (lowered) -> list of sets sorted by set_number.
        # Also flag any top set that had drops attached (new-model dropset) so
        # the UI can show the ↘ marker on the prev hint.
        prev_map: dict[str, list[dict]] = {}
        for ex in prev_session.exercises:
            key = ex.exercise_name.lower()
            child_count: dict = {}
            for s in ex.sets:
                if s.parent_set_id is not None:
                    child_count[s.parent_set_id] = child_count.get(s.parent_set_id, 0) + 1

            sets_data = sorted(
                [
                    {
                        "set_number": s.set_number,
                        "weight_kg": s.weight_kg,
                        "reps": s.reps,
                        "reps_in_reserve": s.reps_in_reserve,
                        "is_warmup": s.is_warmup,
                        # Legacy rows (no parent, is_dropset=true) stay marked.
                        # New top-of-dropset rows flagged via had_drops.
                        "is_dropset": s.is_dropset,
                        "had_drops": child_count.get(s.id, 0) > 0,
                        "description": s.description,
                    }
                    for s in ex.sets
                ],
                key=lambda s: s["set_number"],
            )
            prev_map[key] = sets_data

        return prev_map
