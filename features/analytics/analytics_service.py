from uuid import UUID
from datetime import date, timedelta, datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, and_

from features.workout_session.workout_session_model import WorkoutSession
from features.workout_session.session_exercise_model import SessionExercise
from features.exercise_set.exercise_set_model import ExerciseSet
from features.workout_session.workout_session_enum import SessionStatusEnum


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_session_analytics(
        self,
        user_id: UUID,
        split_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        # Build base query: sessions with their exercises and sets
        query = (
            select(
                cast(WorkoutSession.started_at, Date).label("session_date"),
                WorkoutSession.id.label("session_id"),
                WorkoutSession.duration_seconds,
                func.count(func.distinct(SessionExercise.id)).label("exercise_count"),
                func.count(ExerciseSet.id).label("total_sets"),
                func.coalesce(func.sum(ExerciseSet.reps), 0).label("total_reps"),
                func.coalesce(
                    func.sum(ExerciseSet.weight_kg * ExerciseSet.reps), 0.0
                ).label("total_volume"),
                func.avg(ExerciseSet.reps_in_reserve).label("avg_rir"),
            )
            .select_from(WorkoutSession)
            .outerjoin(SessionExercise, SessionExercise.session_id == WorkoutSession.id)
            .outerjoin(ExerciseSet, ExerciseSet.session_exercise_id == SessionExercise.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
            )
        )

        if split_id:
            query = query.where(WorkoutSession.split_id == split_id)
        if from_date:
            query = query.where(cast(WorkoutSession.started_at, Date) >= from_date)
        if to_date:
            query = query.where(cast(WorkoutSession.started_at, Date) <= to_date)

        query = query.group_by(
            cast(WorkoutSession.started_at, Date),
            WorkoutSession.id,
            WorkoutSession.duration_seconds,
        ).order_by(cast(WorkoutSession.started_at, Date).asc())

        result = await self.db.execute(query)
        rows = result.all()

        sessions = []
        for row in rows:
            sessions.append({
                "date": row.session_date,
                "total_volume": float(row.total_volume),
                "total_sets": row.total_sets,
                "total_reps": row.total_reps,
                "avg_rir": round(float(row.avg_rir), 1) if row.avg_rir is not None else None,
                "duration_seconds": row.duration_seconds,
                "exercise_count": row.exercise_count,
            })

        return {"sessions": sessions}

    async def get_exercise_analytics(
        self,
        user_id: UUID,
        exercise_name: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        query = (
            select(
                cast(WorkoutSession.started_at, Date).label("session_date"),
                WorkoutSession.id.label("session_id"),
                func.max(ExerciseSet.weight_kg).label("max_weight"),
                func.sum(ExerciseSet.weight_kg * ExerciseSet.reps).label("total_volume"),
                func.sum(ExerciseSet.reps).label("total_reps"),
                func.count(ExerciseSet.id).label("total_sets"),
                func.avg(ExerciseSet.reps_in_reserve).label("avg_rir"),
            )
            .select_from(ExerciseSet)
            .join(SessionExercise, ExerciseSet.session_exercise_id == SessionExercise.id)
            .join(WorkoutSession, SessionExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                func.lower(SessionExercise.exercise_name) == exercise_name.lower(),
            )
        )

        if from_date:
            query = query.where(cast(WorkoutSession.started_at, Date) >= from_date)
        if to_date:
            query = query.where(cast(WorkoutSession.started_at, Date) <= to_date)

        query = query.group_by(
            cast(WorkoutSession.started_at, Date),
            WorkoutSession.id,
        ).order_by(cast(WorkoutSession.started_at, Date).asc())

        result = await self.db.execute(query)
        rows = result.all()

        data_points = []
        best_pr = None

        for row in rows:
            max_weight = float(row.max_weight) if row.max_weight else 0.0
            total_reps = row.total_reps or 0
            total_sets = row.total_sets or 0
            total_volume = float(row.total_volume) if row.total_volume else 0.0

            # Epley formula: weight * (1 + reps/30)
            # Use the heaviest set's weight and reps for estimated 1RM
            estimated_1rm = round(max_weight * (1 + total_reps / (total_sets * 30)), 1) if total_sets > 0 else max_weight

            data_points.append({
                "date": row.session_date,
                "session_id": row.session_id,
                "max_weight": max_weight,
                "total_volume": total_volume,
                "total_reps": total_reps,
                "total_sets": total_sets,
                "estimated_1rm": estimated_1rm,
                "avg_rir": round(float(row.avg_rir), 1) if row.avg_rir is not None else None,
            })

            if best_pr is None or estimated_1rm > best_pr["estimated_1rm"]:
                best_pr = {
                    "weight": max_weight,
                    "reps": total_reps,
                    "estimated_1rm": estimated_1rm,
                    "date": row.session_date,
                }

        # Fetch best single-set 1RM for more accurate PR
        pr_query = (
            select(
                ExerciseSet.weight_kg,
                ExerciseSet.reps,
                cast(WorkoutSession.started_at, Date).label("session_date"),
            )
            .select_from(ExerciseSet)
            .join(SessionExercise, ExerciseSet.session_exercise_id == SessionExercise.id)
            .join(WorkoutSession, SessionExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                func.lower(SessionExercise.exercise_name) == exercise_name.lower(),
                ExerciseSet.is_warmup == False,
            )
        )

        pr_result = await self.db.execute(pr_query)
        pr_rows = pr_result.all()

        personal_record = None
        for pr_row in pr_rows:
            e1rm = round(pr_row.weight_kg * (1 + pr_row.reps / 30), 1)
            if personal_record is None or e1rm > personal_record["estimated_1rm"]:
                personal_record = {
                    "weight": pr_row.weight_kg,
                    "reps": pr_row.reps,
                    "estimated_1rm": e1rm,
                    "date": pr_row.session_date,
                }

        return {
            "data_points": data_points,
            "personal_record": personal_record,
        }

    async def get_dashboard_summary(self, user_id: UUID) -> dict:
        today = date.today()
        # Monday of the current week
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        # Sessions this week
        week_query = (
            select(func.count())
            .select_from(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                cast(WorkoutSession.started_at, Date) >= monday,
                cast(WorkoutSession.started_at, Date) <= sunday,
            )
        )
        week_result = await self.db.execute(week_query)
        week_sessions = week_result.scalar() or 0

        # Total completed sessions
        total_query = (
            select(func.count())
            .select_from(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
            )
        )
        total_result = await self.db.execute(total_query)
        total_sessions = total_result.scalar() or 0

        # Current streak: consecutive days with at least one completed session
        dates_query = (
            select(func.distinct(cast(WorkoutSession.started_at, Date)).label("session_date"))
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
            )
            .order_by(cast(WorkoutSession.started_at, Date).desc())
        )
        dates_result = await self.db.execute(dates_query)
        session_dates = [row.session_date for row in dates_result.all()]

        current_streak = 0
        check_date = today
        for d in session_dates:
            if d == check_date:
                current_streak += 1
                check_date -= timedelta(days=1)
            elif d < check_date:
                break

        # Recent personal records: best estimated 1RM per exercise from last 30 days
        thirty_days_ago = today - timedelta(days=30)
        pr_query = (
            select(
                SessionExercise.exercise_name,
                ExerciseSet.weight_kg,
                ExerciseSet.reps,
                cast(WorkoutSession.started_at, Date).label("session_date"),
            )
            .select_from(ExerciseSet)
            .join(SessionExercise, ExerciseSet.session_exercise_id == SessionExercise.id)
            .join(WorkoutSession, SessionExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                ExerciseSet.is_warmup == False,
                cast(WorkoutSession.started_at, Date) >= thirty_days_ago,
            )
        )

        pr_result = await self.db.execute(pr_query)
        pr_rows = pr_result.all()

        # Track best 1RM per exercise
        best_per_exercise = {}
        for row in pr_rows:
            e1rm = round(row.weight_kg * (1 + row.reps / 30), 1)
            name = row.exercise_name
            if name not in best_per_exercise or e1rm > best_per_exercise[name]["estimated_1rm"]:
                best_per_exercise[name] = {
                    "exercise_name": name,
                    "weight": row.weight_kg,
                    "reps": row.reps,
                    "estimated_1rm": e1rm,
                    "date": row.session_date,
                }

        # Sort by estimated 1RM descending, take top 5
        personal_records = sorted(
            best_per_exercise.values(),
            key=lambda x: x["estimated_1rm"],
            reverse=True,
        )[:5]

        return {
            "week_sessions": week_sessions,
            "current_streak": current_streak,
            "total_sessions": total_sessions,
            "personal_records": personal_records,
        }
