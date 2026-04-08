from uuid import UUID
from typing import Optional
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, Date
from sqlalchemy.orm import selectinload

from core.groq_client import groq_client
from features.users.users_model import User
from features.analytics.analytics_service import AnalyticsService
from features.weight_log.weight_log_service import WeightLogService
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_session.session_exercise_model import SessionExercise
from features.workout_session.workout_session_enum import SessionStatusEnum
from features.split_exercise.split_exercise_model import SplitExercise
from .ai_prompts import (
    ANALYSIS_SYSTEM_INSTRUCTION,
    SESSION_COACH_SYSTEM_INSTRUCTION,
    SESSION_PLAN_SYSTEM_INSTRUCTION,
    FITNESS_CHAT_SYSTEM_INSTRUCTION,
    build_session_analysis_prompt,
    build_exercise_analysis_prompt,
    build_weight_analysis_prompt,
    build_session_coach_prompt,
    build_fitness_chat_prompt,
    build_session_plan_prompt,
)


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = AnalyticsService(db)
        self.weight_log = WeightLogService(db)

    # ── helpers ───────────────────────────────────────────────────────

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one()

    # ── analysis endpoints ────────────────────────────────────────────

    async def analyze_sessions(
        self,
        user_id: UUID,
        split_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        question: Optional[str] = None,
    ) -> dict:
        user = await self._get_user(user_id)
        data = await self.analytics.get_session_analytics(
            user_id, split_id, from_date, to_date
        )

        prompt = build_session_analysis_prompt(user, data["sessions"], question)
        return await groq_client.generate_json(
            prompt, system_instruction=ANALYSIS_SYSTEM_INSTRUCTION
        )

    async def analyze_exercise(
        self,
        user_id: UUID,
        exercise_name: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        question: Optional[str] = None,
    ) -> dict:
        user = await self._get_user(user_id)
        data = await self.analytics.get_exercise_analytics(
            user_id, exercise_name, from_date, to_date
        )

        prompt = build_exercise_analysis_prompt(
            user, exercise_name, data["data_points"], data["personal_record"], question
        )
        return await groq_client.generate_json(
            prompt, system_instruction=ANALYSIS_SYSTEM_INSTRUCTION
        )

    async def analyze_weight(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        question: Optional[str] = None,
    ) -> dict:
        user = await self._get_user(user_id)
        analytics = await self.weight_log.get_analytics(user_id, from_date, to_date)

        prompt = build_weight_analysis_prompt(user, analytics, question)
        return await groq_client.generate_json(
            prompt, system_instruction=ANALYSIS_SYSTEM_INSTRUCTION
        )

    # ── fitness chat ──────────────────────────────────────────────────

    async def fitness_chat(
        self,
        user_id: UUID,
        question: str,
        history: list[dict] | None = None,
    ) -> dict:
        user = await self._get_user(user_id)

        # Fetch recent session data (last 4 weeks) for context
        four_weeks_ago = date.today() - timedelta(weeks=4)
        session_data = await self.analytics.get_session_analytics(
            user_id, from_date=four_weeks_ago
        )
        recent_sessions = session_data.get("sessions", [])

        # Fetch weight analytics for context
        try:
            weight_analytics = await self.weight_log.get_analytics(
                user_id, from_date=four_weeks_ago
            )
        except Exception:
            weight_analytics = None

        context_prompt = build_fitness_chat_prompt(
            user, recent_sessions, weight_analytics, question
        )
        answer = await groq_client.generate_with_history(
            context_prompt,
            system_instruction=FITNESS_CHAT_SYSTEM_INSTRUCTION,
            history=history or [],
            max_tokens=512,
        )
        return {"answer": answer}

    # ── session coach ─────────────────────────────────────────────────

    async def session_coach(
        self,
        user_id: UUID,
        session_id: UUID,
        question: str,
    ) -> dict:
        result = await self.db.execute(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.exercises)
                .selectinload(SessionExercise.sets)
            )
            .where(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return {"answer": "Session not found."}

        user = await self._get_user(user_id)

        # Fetch the split plan (exercises with expected sets)
        split_exercises = []
        if session.split_id:
            split_result = await self.db.execute(
                select(SplitExercise)
                .where(SplitExercise.split_id == session.split_id)
                .order_by(SplitExercise.display_order)
            )
            split_exercises = split_result.scalars().all()

        # Fetch last 5 completed sessions for this split
        five_weeks_ago = date.today() - timedelta(weeks=5)
        history_result = await self.db.execute(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.exercises)
                .selectinload(SessionExercise.sets)
            )
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.split_id == session.split_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                cast(WorkoutSession.started_at, Date) >= five_weeks_ago,
                WorkoutSession.id != session_id,
            )
            .order_by(WorkoutSession.started_at.desc())
            .limit(5)
        )
        past_sessions = history_result.scalars().all()

        prompt = build_session_coach_prompt(
            user, session, past_sessions, question, split_exercises
        )
        answer = await groq_client.generate(
            prompt,
            system_instruction=SESSION_COACH_SYSTEM_INSTRUCTION,
            max_tokens=300,
        )
        return {"answer": answer}

    # ── session plan ─────────────────────────────────────────────────

    async def generate_session_plan(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> dict:
        """Generate an AI-recommended session plan with weights/reps for each exercise."""
        result = await self.db.execute(
            select(WorkoutSession).where(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return {"exercises": [], "note": "Session not found."}

        user = await self._get_user(user_id)

        # Fetch split exercises
        split_exercises = []
        if session.split_id:
            split_result = await self.db.execute(
                select(SplitExercise)
                .where(SplitExercise.split_id == session.split_id)
                .order_by(SplitExercise.display_order)
            )
            split_exercises = split_result.scalars().all()

        if not split_exercises:
            return {"exercises": [], "note": "No exercises in this split."}

        # Fetch last 5 completed sessions for this split
        five_weeks_ago = date.today() - timedelta(weeks=5)
        history_result = await self.db.execute(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.exercises)
                .selectinload(SessionExercise.sets)
            )
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.split_id == session.split_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                cast(WorkoutSession.started_at, Date) >= five_weeks_ago,
                WorkoutSession.id != session_id,
            )
            .order_by(WorkoutSession.started_at.desc())
            .limit(5)
        )
        past_sessions = history_result.scalars().all()

        prompt = build_session_plan_prompt(user, split_exercises, past_sessions)
        raw = await groq_client.generate(
            prompt,
            system_instruction=SESSION_PLAN_SYSTEM_INSTRUCTION,
            max_tokens=1500,
        )

        return self._parse_session_plan(raw)

    @staticmethod
    def _parse_session_plan(raw: str) -> dict:
        import json
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            parsed = json.loads(cleaned)
            return {
                "exercises": parsed.get("exercises", []),
                "note": parsed.get("note", ""),
            }
        except json.JSONDecodeError:
            return {
                "exercises": [],
                "note": "Could not generate plan. Ask the AI coach for individual exercise advice.",
            }
