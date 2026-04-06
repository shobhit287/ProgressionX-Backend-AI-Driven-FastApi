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
from .ai_prompts import (
    ANALYSIS_SYSTEM_INSTRUCTION,
    SESSION_COACH_SYSTEM_INSTRUCTION,
    FITNESS_CHAT_SYSTEM_INSTRUCTION,
    build_session_analysis_prompt,
    build_exercise_analysis_prompt,
    build_weight_analysis_prompt,
    build_session_coach_prompt,
    build_fitness_chat_prompt,
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

        three_weeks_ago = date.today() - timedelta(weeks=3)
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
                cast(WorkoutSession.started_at, Date) >= three_weeks_ago,
                WorkoutSession.id != session_id,
            )
            .order_by(WorkoutSession.started_at.desc())
        )
        past_sessions = history_result.scalars().all()

        prompt = build_session_coach_prompt(user, session, past_sessions, question)
        answer = await groq_client.generate(
            prompt,
            system_instruction=SESSION_COACH_SYSTEM_INSTRUCTION,
            max_tokens=300,
        )
        return {"answer": answer}
