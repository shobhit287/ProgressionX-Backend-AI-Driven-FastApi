"""Prompt builders for the export PDF AI summary."""

EXPORT_SYSTEM_INSTRUCTION = (
    "You are an expert strength & conditioning coach writing a training-period report. "
    "Reference concrete numbers from the data. Professional, encouraging tone. No markdown.\n\n"

    "NUTRITION GUIDELINES (use only if weight data is provided):\n"
    "- Cutting: healthy loss 0.3-1.0% bodyweight/week. Faster than 1% → muscle loss risk, eat more. "
    "Slower or gaining → cut calories further.\n"
    "- Bulking: healthy gain 0.2-0.5% bodyweight/week. Faster → excess fat, trim a bit. "
    "Flat or losing → add calories.\n"
    "- Maintenance: weight should stay within ±1% over several weeks. Drift → adjust calories to match.\n"
    "- If weight data is missing or <2 entries, state that clearly and suggest logging weight.\n\n"

    "SPLIT FEEDBACK GUIDELINES (use only if current split is provided):\n"
    "- Compare the executed training (volume, RIR, top exercises) with the programmed split.\n"
    "- Flag under-trained muscle groups (missing direct work, low weekly sets) or overtrained ones (high volume + low RIR).\n"
    "- Recommend concrete tweaks (add/remove/swap exercises, change set counts) only when the data supports it.\n"
    "- If the split is well-aligned with performance, say so explicitly. Don't fabricate issues.\n\n"

    "OUTPUT — strict JSON only, in this exact shape:\n"
    "{\n"
    '  "summary": "3-5 sentence narrative of the period, referencing numbers",\n'
    '  "highlights": ["2-4 concrete wins/trends"],\n'
    '  "suggestions": ["2-4 actionable training tweaks"],\n'
    '  "nutrition_advice": "2-3 sentences: weight trend vs goal, and whether to increase / keep / decrease calories",\n'
    '  "split_feedback": "2-3 sentences on whether the current split needs changes, with specifics"\n'
    "}\n"
    "If weight data is absent, set nutrition_advice to a short note asking the user to log weight. "
    "If no splits are provided, set split_feedback to an empty string. "
    "Every list has max 5 items; every sentence stays short."
)


def build_export_prompt(
    user,
    start_date,
    end_date,
    split_name: str | None,
    exercise_name: str | None,
    metrics: dict,
    sessions: list[dict],
    exercise_breakdown: list[dict] | None,
    weight_summary: dict | None = None,
    splits_overview: list[dict] | None = None,
) -> str:
    profile = (
        f"User profile: {user.first_name}, {user.age}y, "
        f"goal={user.goal.value if user.goal else 'n/a'}, "
        f"training={user.training_type.value if user.training_type else 'n/a'}, "
        f"experience={user.experience_level.value if user.experience_level else 'n/a'}, "
        f"profile_weight={user.weight}kg, height={user.height}cm, "
        f"activity={getattr(user, 'activity_level', None) or 'unspecified'}."
    )

    scope_parts = [f"Date range: {start_date} to {end_date}."]
    if split_name:
        scope_parts.append(f"Filtered to split: {split_name}.")
    if exercise_name:
        scope_parts.append(f"Filtered to exercise: {exercise_name}.")
    scope = " ".join(scope_parts)

    metrics_lines = [
        f"- Sessions completed: {metrics.get('session_count', 0)}",
        f"- Total volume (kg): {metrics.get('total_volume', 0):.0f}",
        f"- Total sets: {metrics.get('total_sets', 0)}",
        f"- Total reps: {metrics.get('total_reps', 0)}",
        f"- Avg session duration (min): {metrics.get('avg_duration_min', 0):.1f}",
        f"- Avg RIR: {metrics.get('avg_rir')}",
        f"- Best estimated 1RM in range: {metrics.get('best_e1rm')}",
    ]

    sessions_lines = []
    for s in sessions[:25]:
        sessions_lines.append(
            f"  {s.get('date')}: vol={s.get('total_volume', 0):.0f}kg, "
            f"sets={s.get('total_sets', 0)}, reps={s.get('total_reps', 0)}, "
            f"rir={s.get('avg_rir')}"
        )

    breakdown_block = ""
    if exercise_breakdown:
        lines = []
        for ex in exercise_breakdown[:15]:
            lines.append(
                f"  {ex['exercise_name']}: sessions={ex['sessions']}, "
                f"volume={ex['total_volume']:.0f}kg, "
                f"top_weight={ex['max_weight']}kg, e1RM={ex['best_e1rm']}"
            )
        breakdown_block = "Per-exercise breakdown:\n" + "\n".join(lines) + "\n\n"

    weight_block = ""
    if weight_summary and weight_summary.get("entries", 0) > 0:
        lines = [
            f"- Entries logged: {weight_summary['entries']}",
            f"- Start weight: {weight_summary.get('start_weight')}kg",
            f"- End weight: {weight_summary.get('end_weight')}kg",
            f"- Total change: {weight_summary.get('total_change')}kg",
            f"- Rate of change: {weight_summary.get('rate_of_change')}kg/week",
        ]
        detailed = weight_summary.get("detailed_entries", [])
        if detailed:
            sample_lines = []
            for entry in detailed[:12]:
                bit = f"  {entry['date']}: {entry['weight_kg']}kg"
                if "waist_cm" in entry:
                    bit += f", waist {entry['waist_cm']}cm"
                if "body_fat_pct" in entry:
                    bit += f", bf {entry['body_fat_pct']}%"
                if "note" in entry:
                    bit += f" — {entry['note']}"
                sample_lines.append(bit)
            lines.append("Recent log entries:\n" + "\n".join(sample_lines))
        weight_block = "Weight data for this range:\n" + "\n".join(lines) + "\n\n"
    else:
        weight_block = "Weight data: none logged in this range.\n\n"

    splits_block = ""
    if splits_overview:
        lines = []
        for sp in splits_overview:
            day = str(sp.get("day", "")).capitalize()
            name = sp.get("name") or ""
            lines.append(f"  {day} — {name}")
            exs = sp.get("exercises") or []
            if not exs:
                lines.append("    (rest / no exercises)")
                continue

            # Group paired superset/giant_set exercises so the AI sees them
            # as one coherent block instead of two unrelated lines.
            entries = []
            consumed: set = set()
            for ex in exs:
                ex_type = str(ex.get("exercise_type") or "standard").lower()
                group = ex.get("superset_group")
                if ex_type in ("superset", "giant_set") and group is not None:
                    if group in consumed:
                        continue
                    consumed.add(group)
                    members = [
                        e for e in exs
                        if str(e.get("exercise_type") or "").lower() == ex_type
                        and e.get("superset_group") == group
                    ]
                    entries.append(("group", ex_type, members))
                else:
                    entries.append(("solo", None, ex))

            for entry in entries:
                if entry[0] == "solo":
                    ex = entry[2]
                    bit = (
                        f"    - {ex['name']} — {ex['default_sets']} sets, "
                        f"{ex['rest_seconds']}s rest"
                    )
                    if ex.get("notes"):
                        bit += f" (notes: {ex['notes']})"
                    lines.append(bit)
                else:
                    label = "Superset" if entry[1] == "superset" else "Giant Set"
                    lines.append(f"    - [{label}]:")
                    for m in entry[2]:
                        lines.append(
                            f"        · {m['name']} — {m['default_sets']} sets, "
                            f"{m['rest_seconds']}s rest"
                        )
        splits_block = "Current weekly split:\n" + "\n".join(lines) + "\n\n"

    return (
        f"{profile}\n\n"
        f"{scope}\n\n"
        f"Aggregate metrics:\n" + "\n".join(metrics_lines) + "\n\n"
        f"Per-session log (up to 25):\n"
        + ("\n".join(sessions_lines) if sessions_lines else "  (no sessions)")
        + "\n\n"
        f"{breakdown_block}"
        f"{weight_block}"
        f"{splits_block}"
        "Write the full JSON report: training summary, 2-4 highlights, 2-4 training suggestions, "
        "nutrition_advice grounded in the weight trend vs the user's goal (increase / keep / decrease calories), "
        "and split_feedback judging whether the current weekly split needs modification based on what was actually trained. "
        "Return JSON only."
    )
