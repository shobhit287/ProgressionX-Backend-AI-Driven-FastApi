import json
from uuid import UUID
from typing import Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import anthropic

from core.config import settings
from features.users.users_model import User
from features.analytics.analytics_service import AnalyticsService
from features.weight_log.weight_log_service import WeightLogService


SYSTEM_PROMPT = (
    "You are a knowledgeable fitness coach analyzing workout data. "
    "Provide specific, actionable advice based on the data. "
    "Be encouraging but honest. "
    "Always respond with valid JSON in this exact format: "
    '{"analysis": "your detailed analysis here", "suggestions": ["suggestion 1", "suggestion 2", ...]}'
)


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.analytics_service = AnalyticsService(db)
        self.weight_log_service = WeightLogService(db)

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one()

    async def _call_claude(self, prompt: str) -> dict:
        message = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        try:
            parsed = json.loads(response_text)
            return {
                "analysis": parsed.get("analysis", response_text),
                "suggestions": parsed.get("suggestions", []),
            }
        except json.JSONDecodeError:
            return {
                "analysis": response_text,
                "suggestions": [],
            }

    async def analyze_sessions(
        self,
        user_id: UUID,
        split_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        question: Optional[str] = None,
    ) -> dict:
        user = await self._get_user(user_id)
        session_data = await self.analytics_service.get_session_analytics(
            user_id, split_id, from_date, to_date
        )

        sessions = session_data["sessions"]

        context = (
            f"User profile: Goal = {user.goal.value}, "
            f"Weight = {user.weight}kg, Height = {user.height}cm, "
            f"Age = {user.age}, Gender = {user.gender.value}\n\n"
            f"Workout session data ({len(sessions)} sessions):\n"
        )

        for s in sessions:
            context += (
                f"- Date: {s['date']}, Volume: {s['total_volume']}kg, "
                f"Sets: {s['total_sets']}, Reps: {s['total_reps']}, "
                f"Avg RIR: {s['avg_rir']}, Duration: {s['duration_seconds']}s, "
                f"Exercises: {s['exercise_count']}\n"
            )

        prompt = (
            f"{context}\n"
            f"Analyze this workout data. Focus on:\n"
            f"1. Training volume trends (increasing, decreasing, or stagnant)\n"
            f"2. Training frequency and consistency\n"
            f"3. Whether the intensity (RIR) is appropriate for the user's goal ({user.goal.value})\n"
            f"4. Recovery indicators (session duration, volume per session)\n"
        )

        if question:
            prompt += f"\nThe user specifically asks: {question}\n"

        return await self._call_claude(prompt)

    async def analyze_exercise(
        self,
        user_id: UUID,
        exercise_name: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        question: Optional[str] = None,
    ) -> dict:
        user = await self._get_user(user_id)
        exercise_data = await self.analytics_service.get_exercise_analytics(
            user_id, exercise_name, from_date, to_date
        )

        data_points = exercise_data["data_points"]
        pr = exercise_data["personal_record"]

        context = (
            f"User profile: Goal = {user.goal.value}, "
            f"Weight = {user.weight}kg\n\n"
            f"Exercise: {exercise_name}\n"
            f"Data points ({len(data_points)} sessions):\n"
        )

        for dp in data_points:
            context += (
                f"- Date: {dp['date']}, Max Weight: {dp['max_weight']}kg, "
                f"Volume: {dp['total_volume']}kg, Reps: {dp['total_reps']}, "
                f"Sets: {dp['total_sets']}, Est 1RM: {dp['estimated_1rm']}kg, "
                f"Avg RIR: {dp['avg_rir']}\n"
            )

        if pr:
            context += (
                f"\nPersonal Record: {pr['weight']}kg x {pr['reps']} reps "
                f"(Est 1RM: {pr['estimated_1rm']}kg) on {pr['date']}\n"
            )

        prompt = (
            f"{context}\n"
            f"Analyze this exercise progression data. Focus on:\n"
            f"1. Progressive overload (is the user getting stronger?)\n"
            f"2. Plateau detection (any stalling periods?)\n"
            f"3. Volume and intensity balance\n"
            f"4. Suggestions for breaking through plateaus if detected\n"
            f"5. Form and technique considerations based on weight/rep patterns\n"
        )

        if question:
            prompt += f"\nThe user specifically asks: {question}\n"

        return await self._call_claude(prompt)

    async def analyze_weight(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        question: Optional[str] = None,
    ) -> dict:
        user = await self._get_user(user_id)
        analytics = await self.weight_log_service.get_analytics(
            user_id, from_date, to_date
        )

        weekly_avgs = analytics["weekly_averages"]

        context = (
            f"User profile: Goal = {user.goal.value}, "
            f"Weight = {user.weight}kg, Height = {user.height}cm, "
            f"Age = {user.age}, Gender = {user.gender.value}\n\n"
            f"Weight log analytics:\n"
            f"Total change: {analytics['total_change']}kg\n"
            f"Rate of change: {analytics['rate_of_change']}kg/week\n"
            f"Total entries: {analytics['entries']}\n\n"
            f"Weekly averages:\n"
        )

        for wa in weekly_avgs:
            context += (
                f"- Week of {wa['week_start']}: {wa['average_weight']}kg "
                f"({wa['entries']} entries)\n"
            )

        goal = user.goal.value
        prompt = f"{context}\n"

        if goal == "cutting":
            prompt += (
                "The user is cutting (trying to lose fat while preserving muscle). Analyze:\n"
                "1. Is the rate of weight loss appropriate (0.5-1% body weight per week is ideal)?\n"
                "2. Are there signs of losing too fast (muscle loss risk) or too slow?\n"
                "3. Weekly consistency of weight logging\n"
                "4. Recommendations for adjusting the cut\n"
            )
        elif goal == "bulking":
            prompt += (
                "The user is bulking (trying to gain muscle). Analyze:\n"
                "1. Is the rate of weight gain appropriate (0.25-0.5% body weight per week)?\n"
                "2. Are there signs of gaining too fast (excess fat gain)?\n"
                "3. Weekly consistency of weight logging\n"
                "4. Recommendations for adjusting the bulk\n"
            )
        else:
            prompt += (
                "The user is maintaining weight. Analyze:\n"
                "1. How stable is the weight?\n"
                "2. Any unexpected trends?\n"
                "3. Weekly consistency of weight logging\n"
                "4. Recommendations for maintaining\n"
            )

        if question:
            prompt += f"\nThe user specifically asks: {question}\n"

        return await self._call_claude(prompt)
