from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Date, cast, func, select, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from features.users.users_model import User
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_session.workout_session_enum import SessionStatusEnum
from features.ai_analysis.llm_call_log_model import LlmCallLog


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    async def get_dashboard(self) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())  # Monday
        month_start = today_start.replace(day=1)

        # User counts
        total_users = await self._scalar(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
        new_today = await self._scalar(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        )
        new_week = await self._scalar(
            select(func.count()).select_from(User).where(User.created_at >= week_start)
        )
        new_month = await self._scalar(
            select(func.count()).select_from(User).where(User.created_at >= month_start)
        )

        # Active users
        active_7d = await self._scalar(
            select(func.count(func.distinct(WorkoutSession.user_id))).where(
                WorkoutSession.started_at >= now - timedelta(days=7)
            )
        )
        active_30d = await self._scalar(
            select(func.count(func.distinct(WorkoutSession.user_id))).where(
                WorkoutSession.started_at >= now - timedelta(days=30)
            )
        )

        # Sessions
        total_sessions = await self._scalar(
            select(func.count()).select_from(WorkoutSession).where(
                WorkoutSession.status == SessionStatusEnum.COMPLETED
            )
        )
        sessions_today = await self._scalar(
            select(func.count()).select_from(WorkoutSession).where(
                and_(
                    WorkoutSession.started_at >= today_start,
                    WorkoutSession.status == SessionStatusEnum.COMPLETED,
                )
            )
        )
        avg_duration = await self._scalar(
            select(func.avg(WorkoutSession.duration_seconds)).where(
                and_(
                    WorkoutSession.status == SessionStatusEnum.COMPLETED,
                    WorkoutSession.started_at >= now - timedelta(days=30),
                )
            )
        )

        # LLM calls
        llm_today = await self._scalar(
            select(func.count()).select_from(LlmCallLog).where(
                LlmCallLog.created_at >= today_start
            )
        )
        llm_month = await self._scalar(
            select(func.count()).select_from(LlmCallLog).where(
                LlmCallLog.created_at >= month_start
            )
        )
        tokens_month = await self._scalar(
            select(
                func.coalesce(func.sum(LlmCallLog.input_tokens), 0)
                + func.coalesce(func.sum(LlmCallLog.output_tokens), 0)
            ).where(LlmCallLog.created_at >= month_start)
        )

        return {
            "total_users": total_users or 0,
            "active_users_7d": active_7d or 0,
            "active_users_30d": active_30d or 0,
            "new_users_today": new_today or 0,
            "new_users_this_week": new_week or 0,
            "new_users_this_month": new_month or 0,
            "total_sessions": total_sessions or 0,
            "sessions_today": sessions_today or 0,
            "avg_session_duration": round(avg_duration, 1) if avg_duration else None,
            "total_llm_calls_today": llm_today or 0,
            "total_llm_calls_month": llm_month or 0,
            "total_tokens_month": tokens_month or 0,
        }

    # ------------------------------------------------------------------
    # Active hours heatmap
    # ------------------------------------------------------------------

    async def get_active_hours(self, days: int = 30) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(
                func.extract("hour", WorkoutSession.started_at).label("hour"),
                func.extract("dow", WorkoutSession.started_at).label("dow"),
                func.count().label("cnt"),
            )
            .where(WorkoutSession.started_at >= since)
            .group_by("hour", "dow")
            .order_by("hour", "dow")
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        buckets = [
            {"hour": int(r.hour), "day_of_week": int(r.dow), "count": r.cnt}
            for r in rows
        ]

        # Peak
        peak = max(buckets, key=lambda b: b["count"]) if buckets else {"hour": 0, "day_of_week": 0}

        return {
            "buckets": buckets,
            "peak_hour": peak["hour"],
            "peak_day": peak["day_of_week"],
        }

    # ------------------------------------------------------------------
    # LLM usage
    # ------------------------------------------------------------------

    async def get_llm_usage(self, days: int = 30) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        base = select(LlmCallLog).where(LlmCallLog.created_at >= since)

        # Totals
        total_calls = await self._scalar(
            select(func.count()).select_from(LlmCallLog).where(LlmCallLog.created_at >= since)
        ) or 0
        total_errors = await self._scalar(
            select(func.count()).select_from(LlmCallLog).where(
                and_(LlmCallLog.created_at >= since, LlmCallLog.status != "success")
            )
        ) or 0
        total_input = await self._scalar(
            select(func.coalesce(func.sum(LlmCallLog.input_tokens), 0)).where(
                LlmCallLog.created_at >= since
            )
        ) or 0
        total_output = await self._scalar(
            select(func.coalesce(func.sum(LlmCallLog.output_tokens), 0)).where(
                LlmCallLog.created_at >= since
            )
        ) or 0
        avg_dur = await self._scalar(
            select(func.avg(LlmCallLog.duration_ms)).where(
                and_(LlmCallLog.created_at >= since, LlmCallLog.status == "success")
            )
        )

        # By endpoint
        endpoint_stmt = (
            select(
                LlmCallLog.endpoint,
                func.count().label("cnt"),
                func.avg(LlmCallLog.duration_ms).label("avg_dur"),
                func.coalesce(func.sum(LlmCallLog.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(LlmCallLog.output_tokens), 0).label("out"),
            )
            .where(LlmCallLog.created_at >= since)
            .group_by(LlmCallLog.endpoint)
            .order_by(func.count().desc())
        )
        ep_result = await self.db.execute(endpoint_stmt)
        by_endpoint = [
            {
                "endpoint": r.endpoint,
                "count": r.cnt,
                "avg_duration_ms": round(r.avg_dur, 1) if r.avg_dur else None,
                "total_input_tokens": r.inp,
                "total_output_tokens": r.out,
            }
            for r in ep_result.all()
        ]

        # Daily trend
        daily_stmt = (
            select(
                cast(LlmCallLog.created_at, Date).label("day"),
                func.count().label("cnt"),
                (
                    func.coalesce(func.sum(LlmCallLog.input_tokens), 0)
                    + func.coalesce(func.sum(LlmCallLog.output_tokens), 0)
                ).label("tokens"),
            )
            .where(LlmCallLog.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
        daily_result = await self.db.execute(daily_stmt)
        daily = [
            {"date": str(r.day), "count": r.cnt, "tokens": r.tokens}
            for r in daily_result.all()
        ]

        # Top users by LLM usage
        top_stmt = (
            select(
                LlmCallLog.user_id,
                func.count().label("cnt"),
            )
            .where(and_(LlmCallLog.created_at >= since, LlmCallLog.user_id.isnot(None)))
            .group_by(LlmCallLog.user_id)
            .order_by(func.count().desc())
            .limit(10)
        )
        top_result = await self.db.execute(top_stmt)
        top_rows = top_result.all()

        top_users = []
        for r in top_rows:
            user_stmt = select(User).where(User.id == r.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if user:
                top_users.append({
                    "user_id": user.id,
                    "email": user.email,
                    "name": f"{user.first_name} {user.last_name}",
                    "call_count": r.cnt,
                })

        return {
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_calls * 100, 2) if total_calls else 0,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "avg_duration_ms": round(avg_dur, 1) if avg_dur else None,
            "by_endpoint": by_endpoint,
            "daily": daily,
            "top_users": top_users,
        }

    # ------------------------------------------------------------------
    # User list
    # ------------------------------------------------------------------

    async def get_users(self, page: int = 1, page_size: int = 20, search: Optional[str] = None) -> dict:
        base = select(User).where(User.is_active == True)

        if search:
            pattern = f"%{search.lower()}%"
            base = base.where(
                func.lower(User.email).like(pattern)
                | func.lower(User.first_name).like(pattern)
                | func.lower(User.last_name).like(pattern)
            )

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = await self._scalar(count_stmt) or 0

        # Paginated users
        stmt = base.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        items = []
        for u in users:
            # Last active
            last_active_stmt = (
                select(func.max(WorkoutSession.started_at))
                .where(WorkoutSession.user_id == u.id)
            )
            last_active = await self._scalar(last_active_stmt)

            # Session count
            sess_count = await self._scalar(
                select(func.count()).select_from(WorkoutSession).where(
                    and_(
                        WorkoutSession.user_id == u.id,
                        WorkoutSession.status == SessionStatusEnum.COMPLETED,
                    )
                )
            ) or 0

            # LLM calls
            llm_count = await self._scalar(
                select(func.count()).select_from(LlmCallLog).where(
                    LlmCallLog.user_id == u.id
                )
            ) or 0

            items.append({
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "goal": u.goal.value if u.goal else "",
                "training_type": u.training_type.value if u.training_type else "",
                "experience_level": u.experience_level.value if u.experience_level else "",
                "role": u.role.value if u.role else "user",
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_active": last_active,
                "total_sessions": sess_count,
                "total_llm_calls": llm_count,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _scalar(self, stmt):
        result = await self.db.execute(stmt)
        return result.scalar()
