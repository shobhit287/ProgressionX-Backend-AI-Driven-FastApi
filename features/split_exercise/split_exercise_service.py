from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete

from .split_exercise_repository import SplitExerciseRepository
from features.workout_split.workout_split_repository import WorkoutSplitRepository
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_session.session_exercise_model import SessionExercise
from features.workout_session.workout_session_enum import SessionStatusEnum


class SplitExerciseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.exercise_repository = SplitExerciseRepository(db)
        self.split_repository = WorkoutSplitRepository(db)

    async def _verify_split_ownership(self, split_id: UUID, user_id: UUID):
        """Verify the split belongs to the user. Raises 404 if not found."""
        return await self.split_repository.get_by_id(split_id, user_id)

    async def create(self, split_id: UUID, user_id: UUID, payload: dict):
        await self._verify_split_ownership(split_id, user_id)

        payload["split_id"] = split_id

        if payload.get("display_order") is None:
            max_order = await self.exercise_repository.get_max_display_order(split_id)
            payload["display_order"] = max_order + 1

        exercise = await self.exercise_repository.create(payload)
        return exercise

    async def get_all_by_split(self, split_id: UUID, user_id: UUID):
        await self._verify_split_ownership(split_id, user_id)
        return await self.exercise_repository.get_all_by_split(split_id)

    async def update(self, split_id: UUID, exercise_id: UUID, user_id: UUID, payload: dict):
        await self._verify_split_ownership(split_id, user_id)
        exercise = await self.exercise_repository.get_by_id(exercise_id)
        updated_exercise = await self.exercise_repository.update(exercise, payload)
        return updated_exercise

    async def delete(self, split_id: UUID, exercise_id: UUID, user_id: UUID):
        await self._verify_split_ownership(split_id, user_id)
        exercise = await self.exercise_repository.get_by_id(exercise_id)

        # Remove this exercise from any active (in-progress) sessions for this split
        active_sessions_result = await self.db.execute(
            select(WorkoutSession.id).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.split_id == split_id,
                WorkoutSession.status == SessionStatusEnum.IN_PROGRESS,
            )
        )
        active_session_ids = [row[0] for row in active_sessions_result.all()]

        if active_session_ids:
            await self.db.execute(
                sql_delete(SessionExercise).where(
                    SessionExercise.session_id.in_(active_session_ids),
                    SessionExercise.split_exercise_id == exercise_id,
                )
            )
            await self.db.flush()

        await self.exercise_repository.delete(exercise)

        # Reorder remaining exercises
        remaining = await self.exercise_repository.get_all_by_split(split_id)
        order_map = []
        new_order = 1
        for ex in remaining:
            if ex.display_order != new_order:
                order_map.append({"id": ex.id, "display_order": new_order})
            new_order += 1

        if order_map:
            await self.exercise_repository.bulk_update_order(order_map)

    async def get_all_exercise_names(self, user_id: UUID) -> list[str]:
        return await self.exercise_repository.get_all_exercise_names(user_id)

    async def reorder(self, split_id: UUID, user_id: UUID, order_items: list[dict]):
        await self._verify_split_ownership(split_id, user_id)
        await self.exercise_repository.bulk_update_order(order_items)

        # Propagate order to in-progress sessions for this split
        active_sessions_result = await self.db.execute(
            select(WorkoutSession.id).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.split_id == split_id,
                WorkoutSession.status == SessionStatusEnum.IN_PROGRESS,
            )
        )
        active_session_ids = [row[0] for row in active_sessions_result.all()]

        if active_session_ids:
            order_by_split_ex = {item["id"]: item["display_order"] for item in order_items}
            existing = await self.db.execute(
                select(SessionExercise).where(
                    SessionExercise.session_id.in_(active_session_ids),
                    SessionExercise.split_exercise_id.in_(order_by_split_ex.keys()),
                )
            )
            for se in existing.scalars().all():
                new_order = order_by_split_ex.get(se.split_exercise_id)
                if new_order is not None and se.display_order != new_order:
                    se.display_order = new_order
            await self.db.flush()

        return await self.exercise_repository.get_all_by_split(split_id)
