"""Workout-history-only PDF export. Distinct from the analytics report
(features/export/export_service.py) — no weight logs, no nutrition, no
split overview. Only the literal session-by-session breakdown plus a
short AI performance summary at the end."""

from __future__ import annotations

import io
import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.email import EmailAttachment, email_service
from core.email.email_templates import export_report_email
from core.groq_client import groq_client, set_llm_context
from db.database import AsyncSessionLocal
from features.exercise_set.exercise_set_model import ExerciseSet
from features.users.users_model import User
from features.workout_session.session_exercise_model import SessionExercise
from features.workout_session.workout_session_enum import SessionStatusEnum
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_split.workout_split_model import WorkoutSplit

logger = logging.getLogger(__name__)


WORKOUT_HISTORY_SYSTEM_INSTRUCTION = (
    "You are a strength-training coach reviewing a single user's workout "
    "history for a specific weekly split. Focus only on session execution: "
    "volume trends, intensity (RIR), set/rep schemes, exercise selection, "
    "and progression across the date range. Do NOT comment on nutrition, "
    "body weight, sleep, or split planning — those are out of scope for "
    "this report. Keep feedback concrete and actionable."
)


def _build_workout_history_prompt(
    user: User,
    split_name: str,
    start_date: date,
    end_date: date,
    sessions: list[dict],
) -> str:
    """Compact LLM prompt — only session execution data. The per-set log is
    capped to a character budget so wide date ranges (e.g. several months)
    don't exceed the model's per-request token limit. The most recent sessions
    are kept — they drive the 'next cycle' suggestions — and any older ones
    that don't fit are noted. This only trims what the AI *summarises*; the PDF
    itself still lists every session and set."""
    # One text block per session so trimming drops whole sessions cleanly
    # instead of cutting one mid-way.
    session_blocks: list[str] = []
    for sess in sessions:
        date_str = sess["date"].isoformat() if sess.get("date") else "?"
        dur_min = (sess.get("duration_seconds") or 0) // 60
        block_lines = [f"- {date_str} · {dur_min} min"]
        for ex in sess.get("exercises", []):
            sets = ex.get("sets") or []
            if not sets:
                continue
            set_strs = []
            for s in sets:
                tag = ""
                if s.get("is_warmup"):
                    tag = "(W)"
                elif s.get("is_drop"):
                    tag = "(↳drop)"
                rir = (
                    f"@RIR{s['reps_in_reserve']}"
                    if s.get("reps_in_reserve") is not None
                    else ""
                )
                rest = (
                    f" rest{s['rest_seconds']}s"
                    if s.get("rest_seconds") is not None
                    else ""
                )
                set_strs.append(
                    f"{s['weight_kg']:g}x{s['reps']}{rir}{tag}{rest}"
                )
            block_lines.append(f"    {ex['name']}: {', '.join(set_strs)}")
        # Skip header-only blocks (session with no logged sets adds nothing).
        if len(block_lines) > 1:
            session_blocks.append("\n".join(block_lines))

    # Keep the most recent sessions that fit the budget. ~4 chars/token, so
    # ~24k chars ≈ 6k tokens of log — well under the model's per-request limit
    # once the system instruction and JSON response are added.
    CHAR_BUDGET = 24000
    kept: list[str] = []
    total = 0
    for block in reversed(session_blocks):  # newest first
        if kept and total + len(block) > CHAR_BUDGET:
            break
        kept.append(block)
        total += len(block)
    kept.reverse()  # restore chronological order
    omitted = len(session_blocks) - len(kept)

    log_blob = "\n".join(kept) if kept else "(no sets logged)"
    if omitted > 0:
        log_blob = (
            f"(Note: {omitted} older session(s) omitted to stay within AI "
            f"limits; showing the {len(kept)} most recent sessions with sets.)\n"
            + log_blob
        )

    return (
        f"User: {user.first_name} {user.last_name or ''} (goal: "
        f"{getattr(user.goal, 'value', user.goal) or 'not set'}, "
        f"experience: "
        f"{getattr(user.experience_level, 'value', user.experience_level) or 'not set'}).\n"
        f"Split: {split_name}\n"
        f"Range: {start_date.isoformat()} to {end_date.isoformat()}\n"
        f"Sessions: {len(sessions)}\n\n"
        f"Session log:\n{log_blob}\n\n"
        "Return strict JSON with these keys:\n"
        '  "summary": one paragraph (3–5 sentences) on the user\'s '
        "execution across these sessions — volume, intensity, consistency, "
        "and any progression visible session-to-session.\n"
        '  "highlights": list of 3–4 short bullet strings — concrete '
        "wins from this period (PRs, new top sets, volume jumps, etc.).\n"
        '  "suggestions": list of 3–4 short bullet strings — concrete '
        "execution-focused tweaks for next cycle (rep ranges, RIR targets, "
        "exercise order, sets that look stalled). No nutrition or sleep "
        "advice. No split-design advice."
    )


class WorkoutHistoryExportService:
    """Generates a PDF that contains only per-session detail for a single
    split + date range, then emails it to the user."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _get_split(self, split_id: UUID, user_id: UUID) -> Optional[WorkoutSplit]:
        result = await self.db.execute(
            select(WorkoutSplit).where(
                WorkoutSplit.id == split_id,
                WorkoutSplit.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _fetch_sessions(
        self,
        user_id: UUID,
        split_id: Optional[UUID],
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Per-session detail: every exercise with every set. Three batched
        queries (sessions → session_exercises → exercise_sets), grouped in
        Python — keeps the request count constant regardless of session
        count.

        When `split_id` is None, sessions across every split in the range
        are returned and each session is annotated with its split label so
        the PDF can group/identify them."""
        sess_query = select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatusEnum.COMPLETED,
            cast(WorkoutSession.started_at, Date) >= start_date,
            cast(WorkoutSession.started_at, Date) <= end_date,
        )
        if split_id is not None:
            sess_query = sess_query.where(WorkoutSession.split_id == split_id)
        sess_query = sess_query.order_by(WorkoutSession.started_at.asc())

        sess_rows = (await self.db.execute(sess_query)).scalars().all()
        if not sess_rows:
            return []

        session_ids = [s.id for s in sess_rows]

        # When exporting across all splits, look up each session's split
        # name/day so the PDF can label it. Single batched query.
        split_meta: dict = {}
        if split_id is None:
            split_ids_in_use = {s.split_id for s in sess_rows if s.split_id}
            if split_ids_in_use:
                sp_rows = (
                    await self.db.execute(
                        select(WorkoutSplit).where(
                            WorkoutSplit.id.in_(split_ids_in_use)
                        )
                    )
                ).scalars().all()
                split_meta = {
                    sp.id: (
                        sp.day.value if hasattr(sp.day, "value") else str(sp.day),
                        sp.name,
                    )
                    for sp in sp_rows
                }

        ex_rows = (
            await self.db.execute(
                select(SessionExercise)
                .where(SessionExercise.session_id.in_(session_ids))
                .order_by(
                    SessionExercise.session_id,
                    SessionExercise.display_order.asc(),
                )
            )
        ).scalars().all()
        ex_ids = [e.id for e in ex_rows]

        sets_rows = []
        if ex_ids:
            sets_rows = (
                await self.db.execute(
                    select(ExerciseSet)
                    .where(ExerciseSet.session_exercise_id.in_(ex_ids))
                    .order_by(
                        ExerciseSet.session_exercise_id,
                        ExerciseSet.set_number.asc(),
                    )
                )
            ).scalars().all()

        sets_by_ex: dict[UUID, list[dict]] = defaultdict(list)
        for s in sets_rows:
            sets_by_ex[s.session_exercise_id].append({
                "set_number": s.set_number,
                "weight_kg": float(s.weight_kg),
                "reps": s.reps,
                "reps_in_reserve": s.reps_in_reserve,
                "is_warmup": bool(s.is_warmup),
                "is_dropset": bool(s.is_dropset),
                "is_drop": s.parent_set_id is not None,
                "description": s.description,
                "rest_seconds": s.rest_seconds,
            })

        exercises_by_session: dict[UUID, list[dict]] = defaultdict(list)
        for e in ex_rows:
            exercises_by_session[e.session_id].append({
                "name": e.exercise_name,
                "exercise_type": (
                    e.exercise_type.value
                    if hasattr(e.exercise_type, "value")
                    else str(e.exercise_type)
                ),
                "superset_group": e.superset_group,
                "display_order": e.display_order,
                "sets": sets_by_ex.get(e.id, []),
            })

        out: list[dict] = []
        for s in sess_rows:
            exercises = exercises_by_session.get(s.id, [])
            total_sets = sum(len(e["sets"]) for e in exercises)
            total_reps = sum(
                st["reps"]
                for e in exercises
                for st in e["sets"]
            )
            total_volume = sum(
                st["weight_kg"] * st["reps"]
                for e in exercises
                for st in e["sets"]
                if not st.get("is_warmup")
            )
            # Annotate split label when running across all splits.
            split_day, split_name_for_session = (None, None)
            if split_id is None and s.split_id in split_meta:
                split_day, split_name_for_session = split_meta[s.split_id]
            out.append({
                "started_at": s.started_at,
                "date": s.started_at.date() if s.started_at else None,
                "duration_seconds": s.duration_seconds or 0,
                "notes": getattr(s, "notes", None),
                "split_day": split_day,
                "split_name": split_name_for_session,
                "exercises": exercises,
                "total_sets": total_sets,
                "total_reps": total_reps,
                "total_volume": total_volume,
            })
        return out

    async def _llm_summary(
        self,
        user: User,
        split_name: str,
        start_date: date,
        end_date: date,
        sessions: list[dict],
    ) -> dict:
        if not sessions:
            return {
                "summary": (
                    "No completed sessions for this split in the selected "
                    "range. Try widening the date range."
                ),
                "highlights": [],
                "suggestions": [],
            }
        prompt = _build_workout_history_prompt(
            user, split_name, start_date, end_date, sessions
        )
        try:
            result = await groq_client.generate_json(
                prompt,
                system_instruction=WORKOUT_HISTORY_SYSTEM_INSTRUCTION,
                max_tokens=800,
            )
            return {
                "summary": result.get("summary") or "",
                "highlights": result.get("highlights") or [],
                "suggestions": result.get("suggestions") or [],
            }
        except Exception as e:
            logger.warning("workout_history.llm.fail user=%s error=%s", user.id, e)
            return {
                "summary": (
                    "AI summary is currently unavailable. The session log "
                    "above reflects every set you logged in this range."
                ),
                "highlights": [],
                "suggestions": [],
            }

    async def generate_pdf(
        self,
        user_id: UUID,
        split_id: Optional[UUID],
        start_date: date,
        end_date: date,
    ) -> tuple[bytes, str]:
        """Returns (pdf_bytes, split_label_for_email).

        `split_id` is optional — when None, the report covers every split
        the user trained on in the date range."""
        user = await self._get_user(user_id)

        if split_id is not None:
            split = await self._get_split(split_id, user_id)
            if split is None:
                raise ValueError("Split not found or does not belong to user.")
            split_label = (
                f"{split.name} ({split.day.value.capitalize()})"
                if hasattr(split.day, "value")
                else f"{split.name} ({str(split.day).capitalize()})"
            )
        else:
            split_label = "All splits"

        sessions = await self._fetch_sessions(
            user_id, split_id, start_date, end_date
        )
        ai = await self._llm_summary(
            user, split_label, start_date, end_date, sessions
        )

        pdf = self._render_pdf(
            user=user,
            split_label=split_label,
            start_date=start_date,
            end_date=end_date,
            sessions=sessions,
            ai=ai,
            include_split_per_session=split_id is None,
        )
        return pdf, split_label

    @classmethod
    async def run_export_job(
        cls,
        user_id: UUID,
        split_id: Optional[UUID],
        start_date: date,
        end_date: date,
    ) -> None:
        """Background entry point: own DB session, generates PDF, emails it.
        Never raises — failures are logged so the worker loop survives."""
        try:
            set_llm_context(user_id=str(user_id), endpoint="export-workout-history")
            async with AsyncSessionLocal() as db:
                service = cls(db)
                user = await service._get_user(user_id)
                pdf_bytes, split_label = await service.generate_pdf(
                    user_id=user_id,
                    split_id=split_id,
                    start_date=start_date,
                    end_date=end_date,
                )

            subject, html_body, text_body = export_report_email(
                first_name=user.first_name,
                start_date=start_date,
                end_date=end_date,
                split_name=split_label,
                exercise_name=None,
            )
            filename = (
                f"progressionx_workout_history_{start_date}_{end_date}.pdf"
            )
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
                context="workout_history_export",
            )
        except Exception as exc:
            logger.error(
                "workout_history.job.fail user=%s split=%s range=%s..%s "
                "error=%s: %s",
                user_id,
                split_id,
                start_date,
                end_date,
                type(exc).__name__,
                exc,
            )

    # ── PDF rendering ─────────────────────────────────────────────────

    def _render_pdf(
        self,
        *,
        user: User,
        split_label: str,
        start_date: date,
        end_date: date,
        sessions: list[dict],
        ai: dict,
        include_split_per_session: bool = False,
    ) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
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
            title="ProgressionX Workout History",
            author=f"{user.first_name} {user.last_name or ''}".strip(),
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
            fontSize=13,
            spaceBefore=12,
            spaceAfter=4,
        )
        h3 = ParagraphStyle(
            "h3",
            parent=styles["Heading3"],
            textColor=colors.HexColor("#475569"),
            fontSize=11,
            spaceBefore=6,
            spaceAfter=2,
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
        # Notes inside the per-set table need a Paragraph (not a raw string)
        # so long text wraps within the column instead of overflowing.
        note_style = ParagraphStyle(
            "set_note",
            parent=body,
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        )

        def _escape_xml(s: str) -> str:
            """Paragraph parses a tiny XML subset, so user-typed `<`, `>`,
            `&` would otherwise break rendering."""
            return (
                s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
            )

        story = []

        def _fmt_date(d):
            return f"{d.day} {d.strftime('%B %Y')}"

        def _fmt_datetime(dt):
            return f"{dt.day} {dt.strftime('%B %Y, %H:%M UTC')}"

        def _fmt_rest(sec):
            """Seconds -> compact 'Xm Ys' / 'Ys'. Em-dash when unknown (first
            set of an exercise, dropset drop, or an implausibly long gap)."""
            if sec is None:
                return "—"
            sec = int(sec)
            m, s = divmod(sec, 60)
            if m and s:
                return f"{m}m {s}s"
            if m:
                return f"{m}m"
            return f"{s}s"

        # ── Header ─────────────────────────────────────────────────────
        story.append(Paragraph("ProgressionX Workout History", h1))
        story.append(
            Paragraph(
                f"{user.first_name} {user.last_name or ''}".strip()
                + f" &nbsp;·&nbsp; Generated {_fmt_datetime(datetime.utcnow())}",
                muted,
            )
        )
        story.append(
            Paragraph(
                f"Range: <b>{_fmt_date(start_date)}</b> to "
                f"<b>{_fmt_date(end_date)}</b> &nbsp;·&nbsp; "
                f"Split: <b>{split_label}</b>",
                body,
            )
        )

        # ── Range stats — only session-execution numbers ──────────────
        total_volume = sum(s.get("total_volume", 0) for s in sessions)
        total_sets = sum(s.get("total_sets", 0) for s in sessions)
        total_reps = sum(s.get("total_reps", 0) for s in sessions)
        story.append(Paragraph("At a Glance", h2))
        rows = [
            ["Sessions", f"{len(sessions)}"],
            ["Total Sets (working)", f"{total_sets}"],
            ["Total Reps", f"{total_reps}"],
            ["Total Volume", f"{total_volume:.0f} kg"],
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

        # ── Session-by-session detail ─────────────────────────────────
        story.append(Paragraph("Sessions", h2))
        if not sessions:
            story.append(
                Paragraph(
                    "No completed sessions for this split in the selected "
                    "range.",
                    muted,
                )
            )
        else:
            story.append(
                Paragraph(
                    "Every set logged, with the rest taken before each set. "
                    "Drop sets are numbered as &lt;parent&gt;.&lt;n&gt; (e.g. "
                    "3.1, 3.2) and tinted purple. Warm-ups are tagged.",
                    muted,
                )
            )
            for sess in sessions:
                story.append(Spacer(1, 8))
                date_str = _fmt_date(sess["date"]) if sess.get("date") else ""
                time_str = (
                    sess["started_at"].strftime("%H:%M")
                    if sess.get("started_at")
                    else ""
                )
                dur_min = (sess.get("duration_seconds") or 0) // 60
                meta_bits = [date_str, time_str]
                if dur_min:
                    meta_bits.append(f"{dur_min} min")
                # When the report covers every split, include each session's
                # own split label in its header so the user can tell which
                # workout day each block belongs to.
                if (
                    include_split_per_session
                    and sess.get("split_day")
                    and sess.get("split_name")
                ):
                    meta_bits.append(
                        f"{str(sess['split_day']).capitalize()} — "
                        f"{sess['split_name']}"
                    )
                meta_bits.append(
                    f"{sess.get('total_sets', 0)} sets · "
                    f"{sess.get('total_volume', 0):.0f} kg"
                )
                story.append(
                    Paragraph(
                        " &nbsp;·&nbsp; ".join(b for b in meta_bits if b),
                        h3,
                    )
                )
                if sess.get("notes"):
                    story.append(Paragraph(f"<i>{sess['notes']}</i>", muted))

                if not sess.get("exercises"):
                    story.append(Paragraph("No exercises logged.", muted))
                    continue

                for ex in sess["exercises"]:
                    type_label = ""
                    et = ex.get("exercise_type")
                    if et and et != "standard":
                        type_label = (
                            f" <font color='#6366f1'>"
                            f"[{et.replace('_', ' ').upper()}]</font>"
                        )
                    superset_label = ""
                    if ex.get("superset_group"):
                        superset_label = (
                            f" <font color='#64748b'>"
                            f"(superset {ex['superset_group']})</font>"
                        )
                    story.append(
                        Paragraph(
                            f"<b>{ex['name']}</b>{type_label}{superset_label}",
                            body,
                        )
                    )

                    sets = ex.get("sets") or []
                    if not sets:
                        story.append(
                            Paragraph("&nbsp;&nbsp;<i>No sets logged.</i>", muted)
                        )
                        continue

                    set_rows = [
                        ["Set", "Weight (kg)", "Reps", "RIR", "Rest", "Type", "Notes"]
                    ]
                    # Re-number sets so drops display as <parent>.<n> (e.g.
                    # 3.1, 3.2, 3.3) and regular sets keep a clean sequential
                    # count (1, 2, 3, 4 …) instead of their raw DB
                    # set_number which would jump over drop rows.
                    parent_num = 0
                    drop_idx = 0
                    for s in sets:
                        is_drop = bool(s.get("is_drop"))
                        if is_drop:
                            drop_idx += 1
                            num_cell = f"{parent_num}.{drop_idx}"
                        else:
                            parent_num += 1
                            drop_idx = 0
                            num_cell = str(parent_num)

                        rir_cell = (
                            str(s["reps_in_reserve"])
                            if s["reps_in_reserve"] is not None
                            else "—"
                        )
                        tags = []
                        if s.get("is_warmup"):
                            tags.append("warmup")
                        if is_drop:
                            tags.append("drop")
                        elif s.get("is_dropset"):
                            tags.append("top")
                        type_cell = ", ".join(tags) if tags else "—"
                        # Wrap notes in a Paragraph so long descriptions wrap
                        # within the column. Plain strings overflow.
                        note_text = (s.get("description") or "").strip()
                        note_cell = (
                            Paragraph(_escape_xml(note_text), note_style)
                            if note_text
                            else "—"
                        )
                        # Drops are back-to-back — show no rest even though the
                        # DB value is NULL anyway.
                        rest_cell = "—" if is_drop else _fmt_rest(s.get("rest_seconds"))
                        set_rows.append(
                            [
                                num_cell,
                                f"{s['weight_kg']:g}",
                                str(s["reps"]),
                                rir_cell,
                                rest_cell,
                                type_cell,
                                note_cell,
                            ]
                        )

                    set_tbl = Table(
                        set_rows,
                        colWidths=[
                            1.5 * cm,
                            2.3 * cm,
                            1.4 * cm,
                            1.4 * cm,
                            2.0 * cm,
                            2.2 * cm,
                            6.4 * cm,
                        ],
                    )
                    style_cmds = [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        # Numeric columns (Weight, Reps, RIR, Rest) right-align;
                        # Set centres; Type left-aligns.
                        ("ALIGN", (1, 0), (4, -1), "RIGHT"),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("ALIGN", (5, 0), (5, -1), "LEFT"),
                        # Top-align all cells so single-line columns line up
                        # cleanly when the Notes paragraph wraps to 2+ lines.
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#e2e8f0")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f8fafc")],
                        ),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                    for i, s in enumerate(sets, start=1):
                        if s.get("is_drop"):
                            style_cmds.append(
                                (
                                    "BACKGROUND",
                                    (0, i),
                                    (-1, i),
                                    colors.HexColor("#eef2ff"),
                                )
                            )
                    set_tbl.setStyle(TableStyle(style_cmds))
                    story.append(set_tbl)
                    story.append(Spacer(1, 3))

        # ── AI summary at the very end ────────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("Performance Summary", h1))
        story.append(Paragraph(ai.get("summary") or "—", body))

        if ai.get("highlights"):
            story.append(Paragraph("Highlights", h2))
            for h in ai["highlights"]:
                story.append(Paragraph(f"• {h}", body))

        if ai.get("suggestions"):
            story.append(Paragraph("Suggestions", h2))
            for s in ai["suggestions"]:
                story.append(Paragraph(f"• {s}", body))

        doc.build(story)
        return buf.getvalue()
