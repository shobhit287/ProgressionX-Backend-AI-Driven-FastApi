"""Prompt builders for the export PDF AI summary."""

EXPORT_SYSTEM_INSTRUCTION = (
    "You are an expert strength coach generating a written report for a user's "
    "training data export. Be specific, reference numbers from the data, and keep "
    "the tone professional but encouraging. "
    "You MUST respond with valid JSON in this exact format and NOTHING else: "
    '{"summary": "3-6 sentence narrative summary referencing concrete metrics", '
    '"highlights": ["bullet 1", "bullet 2", ...], '
    '"suggestions": ["actionable suggestion 1", "actionable suggestion 2", ...]}'
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
) -> str:
    profile = (
        f"User profile: {user.first_name}, {user.age}y, "
        f"goal={user.goal.value if user.goal else 'n/a'}, "
        f"training={user.training_type.value if user.training_type else 'n/a'}, "
        f"experience={user.experience_level.value if user.experience_level else 'n/a'}."
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

    return (
        f"{profile}\n\n"
        f"{scope}\n\n"
        f"Aggregate metrics:\n" + "\n".join(metrics_lines) + "\n\n"
        f"Per-session log (most recent first up to 25):\n"
        + ("\n".join(sessions_lines) if sessions_lines else "  (no sessions)")
        + "\n\n"
        f"{breakdown_block}"
        "Write a concise report summarizing the user's performance over this period, "
        "call out 3-5 highlights (PRs, volume trends, consistency, weaknesses), and "
        "provide 3-5 actionable suggestions tailored to the data and the user's goal. "
        "Return JSON only."
    )
