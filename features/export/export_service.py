import io
import logging
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.email import EmailAttachment, email_service
from core.email.email_templates import export_report_email
from core.groq_client import groq_client
from db.database import AsyncSessionLocal
from features.exercise_set.exercise_set_model import ExerciseSet
from features.split_exercise.split_exercise_model import SplitExercise
from features.users.users_model import User
from features.workout_session.session_exercise_model import SessionExercise
from features.workout_session.workout_session_enum import SessionStatusEnum
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_split.workout_split_model import WorkoutSplit

from .export_prompts import EXPORT_SYSTEM_INSTRUCTION, build_export_prompt

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_filters(self, user_id: UUID) -> dict:
        splits_result = await self.db.execute(
            select(WorkoutSplit)
            .where(WorkoutSplit.user_id == user_id)
            .order_by(WorkoutSplit.day)
        )
        splits = splits_result.scalars().all()

        ex_result = await self.db.execute(
            select(func.distinct(SplitExercise.name))
            .join(WorkoutSplit, WorkoutSplit.id == SplitExercise.split_id)
            .where(WorkoutSplit.user_id == user_id)
            .order_by(SplitExercise.name)
        )
        exercises = [row[0] for row in ex_result.all()]

        return {
            "splits": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "day": s.day.value,
                }
                for s in splits
            ],
            "exercises": exercises,
        }

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _fetch_sessions(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        split_id: Optional[UUID],
        exercise_name: Optional[str],
    ) -> list[dict]:
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
                cast(WorkoutSession.started_at, Date) >= start_date,
                cast(WorkoutSession.started_at, Date) <= end_date,
            )
        )

        if split_id:
            query = query.where(WorkoutSession.split_id == split_id)
        if exercise_name:
            query = query.where(
                func.lower(SessionExercise.exercise_name) == exercise_name.lower()
            )

        query = query.group_by(
            cast(WorkoutSession.started_at, Date),
            WorkoutSession.id,
            WorkoutSession.duration_seconds,
        ).order_by(cast(WorkoutSession.started_at, Date).asc())

        result = await self.db.execute(query)
        rows = result.all()

        sessions = []
        for row in rows:
            sessions.append(
                {
                    "date": row.session_date,
                    "session_id": row.session_id,
                    "duration_seconds": row.duration_seconds or 0,
                    "exercise_count": row.exercise_count,
                    "total_sets": row.total_sets,
                    "total_reps": row.total_reps,
                    "total_volume": float(row.total_volume or 0),
                    "avg_rir": (
                        round(float(row.avg_rir), 1)
                        if row.avg_rir is not None
                        else None
                    ),
                }
            )
        return sessions

    async def _fetch_exercise_breakdown(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        split_id: Optional[UUID],
    ) -> list[dict]:
        query = (
            select(
                SessionExercise.exercise_name.label("name"),
                func.count(func.distinct(WorkoutSession.id)).label("sessions"),
                func.sum(ExerciseSet.weight_kg * ExerciseSet.reps).label("total_volume"),
                func.max(ExerciseSet.weight_kg).label("max_weight"),
                func.sum(ExerciseSet.reps).label("total_reps"),
                func.count(ExerciseSet.id).label("total_sets"),
            )
            .select_from(ExerciseSet)
            .join(SessionExercise, ExerciseSet.session_exercise_id == SessionExercise.id)
            .join(WorkoutSession, SessionExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                cast(WorkoutSession.started_at, Date) >= start_date,
                cast(WorkoutSession.started_at, Date) <= end_date,
                ExerciseSet.is_warmup == False,  # noqa: E712
            )
            .group_by(SessionExercise.exercise_name)
            .order_by(func.sum(ExerciseSet.weight_kg * ExerciseSet.reps).desc())
        )
        if split_id:
            query = query.where(WorkoutSession.split_id == split_id)

        result = await self.db.execute(query)
        rows = result.all()

        breakdown = []
        for row in rows:
            max_w = float(row.max_weight or 0)
            total_reps = row.total_reps or 0
            total_sets = row.total_sets or 0
            avg_reps_per_set = total_reps / total_sets if total_sets else 0
            best_e1rm = (
                round(max_w * (1 + avg_reps_per_set / 30), 1) if max_w else 0
            )
            breakdown.append(
                {
                    "exercise_name": row.name,
                    "sessions": row.sessions,
                    "total_volume": float(row.total_volume or 0),
                    "max_weight": max_w,
                    "total_reps": total_reps,
                    "total_sets": total_sets,
                    "best_e1rm": best_e1rm,
                }
            )
        return breakdown

    async def _fetch_exercise_progression(
        self,
        user_id: UUID,
        exercise_name: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        query = (
            select(
                cast(WorkoutSession.started_at, Date).label("session_date"),
                func.max(ExerciseSet.weight_kg).label("max_weight"),
                func.sum(ExerciseSet.weight_kg * ExerciseSet.reps).label("total_volume"),
                func.sum(ExerciseSet.reps).label("total_reps"),
                func.count(ExerciseSet.id).label("total_sets"),
            )
            .select_from(ExerciseSet)
            .join(SessionExercise, ExerciseSet.session_exercise_id == SessionExercise.id)
            .join(WorkoutSession, SessionExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.COMPLETED,
                func.lower(SessionExercise.exercise_name) == exercise_name.lower(),
                cast(WorkoutSession.started_at, Date) >= start_date,
                cast(WorkoutSession.started_at, Date) <= end_date,
            )
            .group_by(cast(WorkoutSession.started_at, Date))
            .order_by(cast(WorkoutSession.started_at, Date).asc())
        )
        result = await self.db.execute(query)
        points = []
        for row in result.all():
            max_w = float(row.max_weight or 0)
            sets = row.total_sets or 0
            reps = row.total_reps or 0
            avg_reps = reps / sets if sets else 0
            e1rm = round(max_w * (1 + avg_reps / 30), 1) if max_w else 0
            points.append(
                {
                    "date": row.session_date,
                    "max_weight": max_w,
                    "total_volume": float(row.total_volume or 0),
                    "estimated_1rm": e1rm,
                }
            )
        return points

    @staticmethod
    def _aggregate_metrics(
        sessions: list[dict], breakdown: list[dict]
    ) -> dict:
        if not sessions:
            return {
                "session_count": 0,
                "total_volume": 0.0,
                "total_sets": 0,
                "total_reps": 0,
                "avg_duration_min": 0.0,
                "avg_rir": None,
                "best_e1rm": None,
            }
        total_volume = sum(s["total_volume"] for s in sessions)
        total_sets = sum(s["total_sets"] for s in sessions)
        total_reps = sum(s["total_reps"] for s in sessions)
        avg_dur = sum(s["duration_seconds"] for s in sessions) / len(sessions) / 60.0
        rir_vals = [s["avg_rir"] for s in sessions if s["avg_rir"] is not None]
        avg_rir = round(sum(rir_vals) / len(rir_vals), 1) if rir_vals else None
        best_e1rm = max((b["best_e1rm"] for b in breakdown), default=None)
        return {
            "session_count": len(sessions),
            "total_volume": total_volume,
            "total_sets": total_sets,
            "total_reps": total_reps,
            "avg_duration_min": avg_dur,
            "avg_rir": avg_rir,
            "best_e1rm": best_e1rm,
        }

    async def _llm_summary(
        self,
        user: User,
        start_date: date,
        end_date: date,
        split_name: Optional[str],
        exercise_name: Optional[str],
        metrics: dict,
        sessions: list[dict],
        breakdown: list[dict] | None,
    ) -> dict:
        if metrics["session_count"] == 0:
            return {
                "summary": (
                    "No completed sessions in the selected range. Try widening the "
                    "date range or removing filters."
                ),
                "highlights": [],
                "suggestions": [
                    "Log a session to begin tracking progress.",
                ],
            }
        prompt = build_export_prompt(
            user,
            start_date,
            end_date,
            split_name,
            exercise_name,
            metrics,
            sessions,
            breakdown,
        )
        try:
            result = await groq_client.generate_json(
                prompt,
                system_instruction=EXPORT_SYSTEM_INSTRUCTION,
                max_tokens=900,
            )
            return {
                "summary": result.get("summary") or "",
                "highlights": result.get("highlights") or [],
                "suggestions": result.get("suggestions") or [],
            }
        except Exception as e:
            logger.warning(f"LLM summary failed: {e}")
            return {
                "summary": "AI summary is currently unavailable. The metrics above reflect your training in the selected range.",
                "highlights": [],
                "suggestions": [],
            }

    @classmethod
    async def run_export_job(
        cls,
        user_id: UUID,
        start_date: date,
        end_date: date,
        split_id: Optional[UUID],
        exercise_name: Optional[str],
    ) -> None:
        """Background entry point. Opens its own DB session (request-scoped
        session is already closed by the time BackgroundTasks run), generates
        the PDF, and emails it to the user. Never raises — all outcomes are
        logged so a failed job cannot crash the worker loop."""
        try:
            async with AsyncSessionLocal() as db:
                service = cls(db)
                user = await service._get_user(user_id)
                pdf_bytes = await service.generate_pdf(
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                    split_id=split_id,
                    exercise_name=exercise_name,
                )

                split_name = None
                if split_id:
                    split_result = await db.execute(
                        select(WorkoutSplit).where(
                            WorkoutSplit.id == split_id,
                            WorkoutSplit.user_id == user_id,
                        )
                    )
                    sp = split_result.scalar_one_or_none()
                    if sp:
                        split_name = f"{sp.name} ({sp.day.value.capitalize()})"

            subject, html_body, text_body = export_report_email(
                first_name=user.first_name,
                start_date=start_date,
                end_date=end_date,
                split_name=split_name,
                exercise_name=exercise_name,
            )
            filename = f"progressionx_report_{start_date}_{end_date}.pdf"
            await email_service.send(
                to=user.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                attachments=[
                    EmailAttachment(
                        filename=filename,
                        content=pdf_bytes,
                        mime_type="application/pdf",
                    )
                ],
                context="export_report",
            )
        except Exception as exc:
            logger.error(
                "export.job.fail user_id=%s range=%s..%s error=%s: %s",
                user_id,
                start_date,
                end_date,
                type(exc).__name__,
                exc,
            )

    async def generate_pdf(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        split_id: Optional[UUID],
        exercise_name: Optional[str],
    ) -> bytes:
        user = await self._get_user(user_id)

        split_name = None
        if split_id:
            split_result = await self.db.execute(
                select(WorkoutSplit).where(
                    WorkoutSplit.id == split_id,
                    WorkoutSplit.user_id == user_id,
                )
            )
            split = split_result.scalar_one_or_none()
            if split:
                split_name = f"{split.name} ({split.day.value.capitalize()})"

        sessions = await self._fetch_sessions(
            user_id, start_date, end_date, split_id, exercise_name
        )
        breakdown = await self._fetch_exercise_breakdown(
            user_id, start_date, end_date, split_id
        )

        exercise_progression = []
        if exercise_name:
            exercise_progression = await self._fetch_exercise_progression(
                user_id, exercise_name, start_date, end_date
            )

        metrics = self._aggregate_metrics(sessions, breakdown)

        ai = await self._llm_summary(
            user,
            start_date,
            end_date,
            split_name,
            exercise_name,
            metrics,
            sessions,
            breakdown if not exercise_name else None,
        )

        return self._render_pdf(
            user=user,
            start_date=start_date,
            end_date=end_date,
            split_name=split_name,
            exercise_name=exercise_name,
            metrics=metrics,
            sessions=sessions,
            breakdown=breakdown,
            exercise_progression=exercise_progression,
            ai=ai,
        )

    # ── PDF rendering ─────────────────────────────────────────────────

    @staticmethod
    def _render_chart_png(figure) -> io.BytesIO:
        buf = io.BytesIO()
        figure.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
        buf.seek(0)
        return buf

    def _build_volume_chart(self, sessions: list[dict]):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 2.6))
        if sessions:
            dates = [s["date"] for s in sessions]
            volumes = [s["total_volume"] for s in sessions]
            ax.plot(dates, volumes, marker="o", color="#6366f1", linewidth=2)
            ax.fill_between(dates, volumes, alpha=0.15, color="#6366f1")
            ax.set_ylabel("Volume (kg)")
            ax.set_title("Total Volume per Session")
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
        return fig

    def _build_e1rm_chart(self, points: list[dict], exercise_name: str):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 2.6))
        if points:
            dates = [p["date"] for p in points]
            e1rm = [p["estimated_1rm"] for p in points]
            ax.plot(dates, e1rm, marker="o", color="#10b981", linewidth=2)
            ax.set_ylabel("Est. 1RM (kg)")
            ax.set_title(f"{exercise_name} — Estimated 1RM")
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
        return fig

    def _render_pdf(
        self,
        *,
        user: User,
        start_date: date,
        end_date: date,
        split_name: Optional[str],
        exercise_name: Optional[str],
        metrics: dict,
        sessions: list[dict],
        breakdown: list[dict],
        exercise_progression: list[dict],
        ai: dict,
    ) -> bytes:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm,
            title="ProgressionX Performance Report",
            author=f"{user.first_name} {user.last_name}",
        )

        styles = getSampleStyleSheet()
        h1 = ParagraphStyle(
            "h1",
            parent=styles["Heading1"],
            textColor=colors.HexColor("#1e293b"),
            fontSize=20,
            spaceAfter=4,
        )
        h2 = ParagraphStyle(
            "h2",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#334155"),
            fontSize=14,
            spaceBefore=14,
            spaceAfter=6,
        )
        body = ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
        )
        muted = ParagraphStyle(
            "muted",
            parent=body,
            textColor=colors.HexColor("#64748b"),
            fontSize=9,
        )

        story = []

        story.append(Paragraph("ProgressionX Performance Report", h1))
        story.append(
            Paragraph(
                f"{user.first_name} {user.last_name} &nbsp;·&nbsp; "
                f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                muted,
            )
        )

        scope_bits = [f"Range: <b>{start_date}</b> to <b>{end_date}</b>"]
        if split_name:
            scope_bits.append(f"Split: <b>{split_name}</b>")
        if exercise_name:
            scope_bits.append(f"Exercise: <b>{exercise_name}</b>")
        story.append(Paragraph(" &nbsp;·&nbsp; ".join(scope_bits), body))

        # Metrics table
        story.append(Paragraph("Summary Metrics", h2))
        m = metrics
        rows = [
            ["Sessions", f"{m['session_count']}"],
            ["Total Volume", f"{m['total_volume']:.0f} kg"],
            ["Total Sets", f"{m['total_sets']}"],
            ["Total Reps", f"{m['total_reps']}"],
            ["Avg Duration", f"{m['avg_duration_min']:.1f} min"],
            ["Avg RIR", f"{m['avg_rir'] if m['avg_rir'] is not None else '—'}"],
            ["Best Est. 1RM", f"{m['best_e1rm'] if m['best_e1rm'] is not None else '—'} kg"],
        ]
        tbl = Table(rows, colWidths=[5 * cm, 5 * cm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(tbl)

        # Volume chart
        story.append(Paragraph("Volume Trend", h2))
        fig = self._build_volume_chart(sessions)
        chart_buf = self._render_chart_png(fig)
        plt.close(fig)
        story.append(Image(chart_buf, width=17 * cm, height=6.4 * cm))

        # Exercise progression chart
        if exercise_name and exercise_progression:
            story.append(Paragraph(f"{exercise_name} Progression", h2))
            fig2 = self._build_e1rm_chart(exercise_progression, exercise_name)
            chart2_buf = self._render_chart_png(fig2)
            plt.close(fig2)
            story.append(Image(chart2_buf, width=17 * cm, height=6.4 * cm))

        # Per-exercise breakdown (only if not filtered to single exercise)
        if not exercise_name and breakdown:
            story.append(Paragraph("Top Exercises by Volume", h2))
            br_rows = [["Exercise", "Sessions", "Volume (kg)", "Top Wt", "Est 1RM"]]
            for ex in breakdown[:12]:
                br_rows.append(
                    [
                        ex["exercise_name"][:34],
                        str(ex["sessions"]),
                        f"{ex['total_volume']:.0f}",
                        f"{ex['max_weight']:.1f}",
                        f"{ex['best_e1rm']}",
                    ]
                )
            br_tbl = Table(
                br_rows, colWidths=[6.5 * cm, 2.2 * cm, 3 * cm, 2.5 * cm, 2.5 * cm]
            )
            br_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(br_tbl)

        # AI Summary
        story.append(PageBreak())
        story.append(Paragraph("AI Summary", h1))
        story.append(Paragraph(ai.get("summary") or "—", body))

        if ai.get("highlights"):
            story.append(Paragraph("Highlights", h2))
            for h in ai["highlights"]:
                story.append(Paragraph(f"• {h}", body))

        if ai.get("suggestions"):
            story.append(Paragraph("Suggestions", h2))
            for s in ai["suggestions"]:
                story.append(Paragraph(f"• {s}", body))

        # Session log
        if sessions:
            story.append(Paragraph("Session Log", h2))
            log_rows = [["Date", "Sets", "Reps", "Volume (kg)", "Avg RIR", "Dur (min)"]]
            for s in sessions:
                log_rows.append(
                    [
                        str(s["date"]),
                        str(s["total_sets"]),
                        str(s["total_reps"]),
                        f"{s['total_volume']:.0f}",
                        f"{s['avg_rir']}" if s["avg_rir"] is not None else "—",
                        f"{(s['duration_seconds'] or 0) / 60:.0f}",
                    ]
                )
            log_tbl = Table(
                log_rows,
                colWidths=[3.2 * cm, 2 * cm, 2 * cm, 3.2 * cm, 2.6 * cm, 2.6 * cm],
            )
            log_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(log_tbl)

        doc.build(story)
        return buf.getvalue()
