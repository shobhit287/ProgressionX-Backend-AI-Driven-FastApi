from uuid import UUID
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.groq_client import groq_client
from features.users.users_model import User
from features.weight_log.weight_log_service import WeightLogService
from .diet_repository import DietRepository


DIET_CHAT_SYSTEM_INSTRUCTION = (
    "You are a knowledgeable nutrition coach inside a gym tracking app called ProgressionX. "
    "You have access to the user's profile (weight, height, age, gender, goal, training type, activity level), "
    "their current diet plan, and their weight logs for the last 1-2 months. "
    "Use ALL this data to give personalized, specific, actionable diet advice. "
    "When answering questions about weight gain/loss, compare their weight trend over weeks — "
    "look at the rate of change, consistency, and any notes about cheat meals. "
    "If the user asks about calorie adjustments, calculate based on their actual progress, not just formulas. "
    "Keep answers concise (3-6 sentences), practical, and specific to their data. "
    "Respond in plain text. Do not use markdown formatting."
)

DIET_GENERATE_SYSTEM_INSTRUCTION = (
    "You are an expert nutrition coach. Generate a complete daily diet plan for the user "
    "based on their profile (weight, height, age, gender, goal, training type, activity level). "
    "The diet should be practical, with specific meal times, food items, and quantities. "
    "Use Indian food items since the user's existing diet suggests Indian cuisine preference. "
    "Include supplements if appropriate. "
    "Format the diet as a clean, time-based meal plan (e.g., '9:00am - 50gm paneer + 1tbsp chia seeds'). "
    "Add a note at the bottom with estimated total calories and macros. "
    "Respond in plain text only. No markdown."
)


class DietService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DietRepository(db)
        self.weight_log = WeightLogService(db)

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def get_plan(self, user_id: UUID):
        return await self.repository.get_by_user(user_id)

    async def save_plan(self, user_id: UUID, content: str):
        return await self.repository.upsert(user_id, content)

    async def delete_plan(self, user_id: UUID):
        plan = await self.repository.get_by_user(user_id)
        if plan:
            await self.repository.delete(plan)

    def _build_user_context(self, user: User) -> str:
        training = user.training_type.value if user.training_type else "hypertrophy"
        ctx = (
            f"User profile: {user.first_name}, {user.age}yo {user.gender.value}, "
            f"{user.weight}kg, {user.height}cm\n"
            f"Goal: {user.goal.value}, Experience Level: {user.experience_level.value}, Training type: {training}\n"
        )
        if user.activity_level:
            ctx += f"Activity level: {user.activity_level}\n"
        return ctx

    async def _build_weight_context(self, user_id: UUID) -> str:
        try:
            two_months_ago = date.today() - timedelta(days=60)
            analytics = await self.weight_log.get_analytics(user_id, from_date=two_months_ago)

            ctx = "\nWeight logs (last 2 months):\n"
            ctx += f"Total change: {analytics['total_change']}kg, Rate: {analytics['rate_of_change']}kg/week\n"

            # Get individual entries for detail
            result = await self.weight_log.get_all(user_id, from_date=two_months_ago, page_size=30)
            logs = result.get("items", []) if isinstance(result, dict) else []
            if logs:
                ctx += "Entries:\n"
                for log in logs[-20:]:  # last 20 entries max
                    log_date = log.logged_at.strftime("%Y-%m-%d") if log.logged_at else "?"
                    entry = f"  {log_date}: {log.weight_kg}kg"
                    if log.waist_cm:
                        entry += f", waist {log.waist_cm}cm"
                    if log.body_fat_pct:
                        entry += f", bf {log.body_fat_pct}%"
                    if log.description:
                        entry += f" (note: {log.description})"
                    ctx += entry + "\n"
            return ctx
        except Exception:
            return "\nNo weight logs available.\n"

    async def chat(self, user_id: UUID, question: str, history: list[dict] | None = None) -> dict:
        user = await self._get_user(user_id)
        user_ctx = self._build_user_context(user)
        weight_ctx = await self._build_weight_context(user_id)

        # Get current diet plan
        plan = await self.repository.get_by_user(user_id)
        diet_ctx = ""
        if plan:
            diet_ctx = f"\nCurrent diet plan:\n{plan.content}\n"
        else:
            diet_ctx = "\nNo diet plan saved yet.\n"

        prompt = f"{user_ctx}{diet_ctx}{weight_ctx}\nUser's question: {question}"

        answer = await groq_client.generate_with_history(
            prompt,
            system_instruction=DIET_CHAT_SYSTEM_INSTRUCTION,
            history=history or [],
            max_tokens=600,
        )
        return {"answer": answer}

    async def generate_diet(self, user_id: UUID, preferences: str | None = None) -> dict:
        user = await self._get_user(user_id)
        user_ctx = self._build_user_context(user)
        weight_ctx = await self._build_weight_context(user_id)

        # Get existing diet for reference
        plan = await self.repository.get_by_user(user_id)
        existing_ctx = ""
        if plan:
            existing_ctx = f"\nUser's current diet (for reference, they may want improvements):\n{plan.content}\n"

        prompt = (
            f"{user_ctx}{weight_ctx}{existing_ctx}\n"
            f"Generate a complete daily diet plan for this user. "
        )
        if preferences:
            prompt += f"User preferences/restrictions: {preferences}\n"

        diet = await groq_client.generate(
            prompt,
            system_instruction=DIET_GENERATE_SYSTEM_INSTRUCTION,
            max_tokens=1200,
        )
        return {"diet": diet}
