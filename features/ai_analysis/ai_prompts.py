"""
Centralised prompt templates for AI analysis features.

Each builder receives pre-fetched data and returns a ready-to-send prompt string.
System instructions are module-level constants.
"""

# ── system instructions ──────────────────────────────────────────────

ANALYSIS_SYSTEM_INSTRUCTION = (
    "You are a knowledgeable fitness coach analyzing workout data. "
    "Provide specific, actionable advice based on the data. "
    "Be encouraging but honest. "
    "Always respond with valid JSON in this exact format: "
    '{"analysis": "your detailed analysis here", "suggestions": ["suggestion 1", "suggestion 2", ...]}'
)

SESSION_COACH_SYSTEM_INSTRUCTION = (
    "You are a real-time gym coach embedded in a workout tracking app. "
    "The user is mid-session and asking you a quick question about their current workout. "
    "You have access to their current session logs (sets done so far) and their "
    "previous 2-3 weeks of sessions for the same muscle group/split. "
    "Give SHORT, direct, actionable advice. No fluff. "
    "Consider their recent progression, fatigue indicators (RIR trends), and volume. "
    "If they ask about weight selection, look at their recent performance on that exercise "
    "and give a specific recommendation with reasoning. "
    "Respond in plain text, 2-4 sentences max. Be like a spotter who knows their history."
)


# ── prompt builders ──────────────────────────────────────────────────

def build_session_analysis_prompt(
    user,
    sessions: list[dict],
    question: str | None = None,
) -> str:
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

    return prompt


def build_exercise_analysis_prompt(
    user,
    exercise_name: str,
    data_points: list[dict],
    personal_record: dict | None,
    question: str | None = None,
) -> str:
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

    if personal_record:
        context += (
            f"\nPersonal Record: {personal_record['weight']}kg x {personal_record['reps']} reps "
            f"(Est 1RM: {personal_record['estimated_1rm']}kg) on {personal_record['date']}\n"
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

    return prompt


def build_weight_analysis_prompt(
    user,
    analytics: dict,
    question: str | None = None,
) -> str:
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

    return prompt


def build_session_coach_prompt(
    user,
    session,
    past_sessions: list,
    question: str,
) -> str:
    # Current session context
    current_ctx = "=== CURRENT SESSION (in progress) ===\n"
    for ex in session.exercises:
        current_ctx += f"\n{ex.exercise_name}:\n"
        if not ex.sets:
            current_ctx += "  (no sets logged yet)\n"
        for s in ex.sets:
            warmup = " [WARMUP]" if s.is_warmup else ""
            dropset = " [DROPSET]" if s.is_dropset else ""
            rir = f", RIR {s.reps_in_reserve}" if s.reps_in_reserve is not None else ""
            current_ctx += f"  Set {s.set_number}: {s.weight_kg}kg x {s.reps} reps{rir}{warmup}{dropset}\n"

    # History context
    history_ctx = f"\n=== PREVIOUS SESSIONS (same split, last 3 weeks: {len(past_sessions)} sessions) ===\n"
    for ps in past_sessions:
        ps_date = ps.started_at.strftime("%a, %b %d") if ps.started_at else "?"
        history_ctx += f"\n--- {ps_date} ---\n"
        for ex in ps.exercises:
            history_ctx += f"{ex.exercise_name}:\n"
            for s in ex.sets:
                warmup = " [W]" if s.is_warmup else ""
                dropset = " [D]" if s.is_dropset else ""
                rir = f", RIR {s.reps_in_reserve}" if s.reps_in_reserve is not None else ""
                history_ctx += f"  Set {s.set_number}: {s.weight_kg}kg x {s.reps}{rir}{warmup}{dropset}\n"

    return (
        f"User: {user.goal.value} phase, {user.weight}kg bodyweight\n\n"
        f"{current_ctx}\n{history_ctx}\n"
        f"User's question: {question}"
    )
