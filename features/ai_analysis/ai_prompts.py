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

FITNESS_CHAT_SYSTEM_INSTRUCTION = (
    "You are a knowledgeable fitness assistant inside a gym tracking app called ProgressionX. "
    "You ONLY answer questions related to fitness, exercise, workout programming, diet, nutrition, "
    "supplements, recovery, injury prevention, body composition, and health goals. "
    "If the user asks anything unrelated to fitness or health, politely decline and redirect them "
    "to ask a fitness-related question instead. "
    "You have access to the user's profile and recent training/weight data — use it to personalize your answers. "
    "Keep answers concise (3-6 sentences), practical, and actionable. "
    "Respond in plain text. Do not use markdown formatting."
)

SESSION_PLAN_SYSTEM_INSTRUCTION = (
    "You are an expert strength coach generating a pre-workout plan. "
    "Given the user's split plan (exercises + target sets) and their last 4-5 sessions of performance data, "
    "generate a recommended session with specific weights, reps, and warmup sets for each exercise. "
    "Rules for weight recommendations:\n"
    "1. Look at the trend across sessions — if performance is consistent, suggest a small increase (1-2.5kg for upper, 2.5-5kg for lower).\n"
    "2. If the user missed sessions recently, be conservative — recommend the same or slightly lower weight.\n"
    "3. If RIR was very low (0-1) last session, keep the weight the same and aim for more reps.\n"
    "4. If RIR was high (3+), suggest increasing weight.\n"
    "5. Include 1-2 warmup sets for compound movements ramping up to working weight.\n"
    "6. Use realistic weight increments (2.5kg jumps for barbells, 1-2kg for dumbbells).\n"
    "7. Respect the user's training style and goal — adjust rep ranges accordingly.\n"
    "You MUST respond with valid JSON in this exact format:\n"
    '{"exercises": [{"exerciseName": "Exercise Name", "sets": [{"setNumber": 1, "weightKg": 20, "reps": 12, "isWarmup": true}, '
    '{"setNumber": 2, "weightKg": 30, "reps": 10, "isWarmup": false}]}], "note": "brief one-line note about the plan"}\n'
    "Do NOT include any text outside the JSON. Only JSON."
)

SESSION_COACH_SYSTEM_INSTRUCTION = (
    "You are a real-time gym coach embedded in a workout tracking app. "
    "The user is mid-session and asking you a quick question about their current workout. "
    "You have access to their split plan (exercises + target sets), current session logs, "
    "and their previous 4-5 sessions for the same split. "
    "Give SHORT, direct, actionable advice. No fluff. "
    "Consider their recent progression, fatigue indicators (RIR trends), and volume. "
    "IMPORTANT: When the user asks about 'next weight', 'next set', or 'this exercise' "
    "WITHOUT specifying an exercise name, figure out which exercise they mean by: "
    "1) Check if any exercise has fewer completed sets than the target sets in the split plan — "
    "that exercise likely has sets remaining, so the user is asking about it. "
    "2) If all sets for the current exercise are done, they are likely asking about the NEXT exercise in the split order. "
    "3) Use the split plan order to determine what comes next. "
    "If they ask about weight selection, look at their recent performance on that exercise "
    "and give a specific number recommendation with reasoning. "
    "Consider the user's training style (hypertrophy, strength, etc.) and goal (bulking, cutting, maintenance) "
    "when recommending weights and rep ranges. "
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


def build_fitness_chat_prompt(
    user,
    recent_sessions: list[dict],
    weight_analytics: dict | None,
    question: str,
) -> str:
    context = (
        f"User profile: Name = {user.first_name}, Goal = {user.goal.value}, "
        f"Weight = {user.weight}kg, Height = {user.height}cm, "
        f"Age = {user.age}, Gender = {user.gender.value}\n\n"
    )

    if recent_sessions:
        context += f"Recent workout sessions ({len(recent_sessions)} sessions, last 4 weeks):\n"
        for s in recent_sessions:
            context += (
                f"- Date: {s['date']}, Volume: {s['total_volume']}kg, "
                f"Sets: {s['total_sets']}, Reps: {s['total_reps']}, "
                f"Avg RIR: {s['avg_rir']}, Duration: {s['duration_seconds']}s, "
                f"Exercises: {s['exercise_count']}\n"
            )
    else:
        context += "No recent workout sessions found.\n"

    if weight_analytics and weight_analytics.get("entries", 0) > 0:
        context += (
            f"\nWeight log: Total change = {weight_analytics['total_change']}kg, "
            f"Rate = {weight_analytics['rate_of_change']}kg/week, "
            f"Entries = {weight_analytics['entries']}\n"
        )

    return f"{context}\nUser's question: {question}"


def build_session_coach_prompt(
    user,
    session,
    past_sessions: list,
    question: str,
    split_exercises: list | None = None,
) -> str:
    # Split plan context (target exercises and sets)
    split_ctx = ""
    if split_exercises:
        split_ctx = "=== SPLIT PLAN (target exercises & sets for this session) ===\n"
        for i, se in enumerate(split_exercises, 1):
            split_ctx += f"  {i}. {se.name} — {se.default_sets} sets"
            if se.notes:
                split_ctx += f" (notes: {se.notes})"
            split_ctx += "\n"
        split_ctx += "\n"

    # Build a map of exercise name -> target sets from split plan
    target_sets_map = {}
    if split_exercises:
        for se in split_exercises:
            target_sets_map[se.name.lower()] = se.default_sets

    # Current session context with completion status
    current_ctx = "=== CURRENT SESSION (in progress) ===\n"
    for ex in session.exercises:
        completed_sets = len([s for s in ex.sets if not s.is_warmup])
        target = target_sets_map.get(ex.exercise_name.lower(), "?")
        status = "DONE" if target != "?" and completed_sets >= target else f"{completed_sets}/{target} sets done"
        current_ctx += f"\n{ex.exercise_name} [{status}]:\n"
        if not ex.sets:
            current_ctx += "  (no sets logged yet)\n"
        for s in ex.sets:
            warmup = " [WARMUP]" if s.is_warmup else ""
            dropset = " [DROPSET]" if s.is_dropset else ""
            rir = f", RIR {s.reps_in_reserve}" if s.reps_in_reserve is not None else ""
            current_ctx += f"  Set {s.set_number}: {s.weight_kg}kg x {s.reps} reps{rir}{warmup}{dropset}\n"

    # History context
    history_ctx = f"\n=== PREVIOUS SESSIONS (same split, last {len(past_sessions)} sessions) ===\n"
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

    training = user.training_type.value if hasattr(user, 'training_type') and user.training_type else "hypertrophy"
    return (
        f"User: {user.goal.value} phase, {user.weight}kg bodyweight, training style: {training}\n\n"
        f"{split_ctx}{current_ctx}\n{history_ctx}\n"
        f"User's question: {question}"
    )


def build_session_plan_prompt(
    user,
    split_exercises: list,
    past_sessions: list,
) -> str:
    # Split plan
    plan_ctx = "=== TODAY'S SPLIT PLAN ===\n"
    for i, se in enumerate(split_exercises, 1):
        plan_ctx += f"  {i}. {se.name} — {se.default_sets} working sets"
        if se.notes:
            plan_ctx += f" (notes: {se.notes})"
        plan_ctx += "\n"

    # Past sessions with dates (including gaps)
    history_ctx = ""
    if past_sessions:
        history_ctx = f"\n=== PREVIOUS SESSIONS ({len(past_sessions)} sessions, most recent first) ===\n"
        for ps in past_sessions:
            ps_date = ps.started_at.strftime("%Y-%m-%d (%a)") if ps.started_at else "?"
            history_ctx += f"\n--- {ps_date} ---\n"
            for ex in ps.exercises:
                history_ctx += f"{ex.exercise_name}:\n"
                for s in ex.sets:
                    warmup = " [WARMUP]" if s.is_warmup else ""
                    dropset = " [DROPSET]" if s.is_dropset else ""
                    rir = f", RIR {s.reps_in_reserve}" if s.reps_in_reserve is not None else ""
                    history_ctx += f"  Set {s.set_number}: {s.weight_kg}kg x {s.reps}{rir}{warmup}{dropset}\n"
    else:
        history_ctx = "\n=== NO PREVIOUS SESSIONS FOUND ===\nThis is the user's first time doing this split. Suggest conservative starting weights.\n"

    training = user.training_type.value if hasattr(user, 'training_type') and user.training_type else "hypertrophy"
    return (
        f"User: {user.goal.value} phase, {user.weight}kg bodyweight, training style: {training}\n"
        f"Today's date: {__import__('datetime').date.today().strftime('%Y-%m-%d (%A)')}\n\n"
        f"{plan_ctx}\n{history_ctx}\n"
        f"Generate a complete recommended session plan with specific weights and reps for EVERY exercise in the split plan. "
        f"Follow the exercise order from the split plan. "
        f"Include warmup sets for the first 1-2 compound exercises. "
        f"The user's training style is {training} — adjust rep ranges accordingly "
        f"(hypertrophy: 8-12 reps, strength: 3-6 reps, powerbuilding: mix of both, endurance: 12-20 reps, general_fitness: 8-15 reps)."
    )
