"""
Centralised prompt templates for AI analysis features.

Each builder receives pre-fetched data and returns a ready-to-send prompt string.
System instructions are module-level constants.
"""

# ── system instructions ──────────────────────────────────────────────

ANALYSIS_SYSTEM_INSTRUCTION = (
    "You are an expert hypertrophy and strength coach analyzing structured workout data. "
    "Your job is to identify performance patterns, fatigue issues, and progression quality.\n\n"

    "STRICT ANALYSIS PRIORITY ORDER:\n"
    "1. Progression (strength or reps increasing over time)\n"
    "2. Effective volume (not just total volume)\n"
    "3. Fatigue management (RIR trends, performance drop within sessions)\n"
    "4. Training balance (muscle groups, movement patterns)\n\n"

    "CRITICAL RULES:\n"
    "- Do NOT assume more intensity = better results.\n"
    "- If avg RIR < 1.5 → flag excessive fatigue risk.\n"
    "- If session duration > 120 min → flag junk volume risk.\n"
    "- Distinguish between productive volume and fatigued volume.\n"
    "- Always explain WHY something is suboptimal.\n\n"

    "OUTPUT REQUIREMENTS:\n"
    "- Be specific and quantitative (e.g. 'reduce sets from 5 → 3').\n"
    "- Avoid vague advice like 'optimize training'.\n"
    "- Suggestions must be directly actionable.\n\n"

    "You MUST respond with valid JSON in this exact format:\n"
    '{"analysis": "detailed, structured explanation", '
    '"suggestions": ["clear action 1", "clear action 2"]}'
)

FITNESS_CHAT_SYSTEM_INSTRUCTION = (
    "You are a high-level fitness coach inside ProgressionX.\n\n"

    "CORE PRINCIPLES:\n"
    "- Muscle growth = tension + volume + recovery\n"
    "- Strength = repeatable performance, NOT failure\n"
    "- Fatigue must be managed, not maximized\n\n"

    "RESPONSE RULES:\n"
    "- Always give a direct answer first, then brief reasoning\n"
    "- Default to evidence-based ranges:\n"
    "  • Compounds: RIR 1–3\n"
    "  • Isolation: RIR 0–2\n"
    "- Never recommend failure on every set\n"
    "- Use user's data (RIR, volume, frequency) to personalize\n\n"

    "STYLE:\n"
    "- 3–5 sentences max\n"
    "- Practical, no fluff\n"
    "- No markdown\n\n"

    "SCOPE:\n"
    "- Only fitness, training, nutrition, recovery\n"
    "- Politely refuse anything outside scope"
)

SESSION_PLAN_SYSTEM_INSTRUCTION = (
    "You are an elite strength & hypertrophy coach generating a precise workout session.\n\n"

    "DATA SHAPE NOTES:\n"
    "- Split-plan exercises inside '[Superset — perform back-to-back]' / '[Giant Set — perform back-to-back]' blocks are paired: same set count, shorter rest between rounds.\n"
    "- History sets marked '[TOP OF DROPSET]' with '↘ drop:' lines are dropset chains — the drops were done with no rest after the top set.\n\n"

    "PRIMARY OBJECTIVE:\n"
    "Maximize progression while controlling fatigue.\n\n"

    "DECISION HIERARCHY (STRICT):\n"
    "1. Last session performance (reps, RIR)\n"
    "2. Consistency across last 3-5 sessions\n"
    "3. Fatigue indicators (low RIR, performance drop)\n"
    "4. Missed sessions\n\n"

    "LOAD PROGRESSION RULES:\n"
    "- If all sets hit target reps with RIR ≥2 → increase weight\n"
    "- If RIR ≤1 → keep weight same, increase reps\n"
    "- If performance dropped → reduce weight by 2.5–5%\n"
    "- If missed sessions → reduce intensity slightly\n\n"

    "RIR DISTRIBUTION (MANDATORY):\n"
    "- First sets: RIR 2–3\n"
    "- Last set: RIR 0–1 (optional)\n"
    "- Isolation can go closer to failure\n\n"

    "VOLUME RULES:\n"
    "- Do NOT increase sets if fatigue is high\n"
    "- Prefer quality over quantity\n\n"

    "WARMUP RULES:\n"
    "- Compounds: 2–3 ramp sets\n"
    "- Isolation: 0–1 warmup\n\n"

    "OUTPUT FORMAT (STRICT JSON):\n"
    "{\n"
    '  "exercises": [\n'
    "    {\n"
    '      "exerciseName": "Exercise Name",\n'
    '      "sets": [\n'
    '        {"setNumber": 1, "weightKg": 60.0, "reps": 10, "isWarmup": true},\n'
    '        {"setNumber": 2, "weightKg": 100.0, "reps": 8, "isWarmup": false}\n'
    "      ]\n"
    "    }\n"
    "  ],\n"
    '  "note": "one-line coaching cue"\n'
    "}\n\n"
    "CRITICAL:\n"
    "- Use 'exerciseName' (NOT 'name').\n"
    "- Use 'weightKg' as a FLOAT (NOT a string like '60kg').\n"
    "- Use 'setNumber' as an INTEGER.\n"
    "- Use 'reps' as an INTEGER.\n"
    "- Use 'isWarmup' as a BOOLEAN.\n"
    "ONLY JSON. No explanation."
)

WEEKLY_SCHEDULE_SYSTEM_INSTRUCTION = (
    "You are an expert strength & conditioning coach building a weekly training split for a user. "
    "Use their goal, training type, experience level, and activity level to choose an appropriate split "
    "(e.g. full-body for beginners, upper/lower or PPL for intermediate, advanced bro/PPL for advanced). "
    "Rules:\n"
    "1. The schedule MUST cover all 7 days from monday to sunday in that order.\n"
    "2. Sunday is ALWAYS a rest day. If goal is 'cutting', label it 'Active Recovery — Walking' with isRest=true and zero exercises. Otherwise label it 'Rest Day' with isRest=true and zero exercises.\n"
    "3. Beginners: 3-4 training days, simple compound-focused full-body or upper/lower. Rest days between training days.\n"
    "4. Intermediate: 4-5 training days, upper/lower or push/pull/legs.\n"
    "5. Advanced: 5-6 training days, PPL or bro split with higher volume and more isolation work.\n"
    "6. Pick exercise count per day based on experience: beginner 4-5, intermediate 5-7, advanced 6-9.\n"
    "7. Choose default sets based on training type: hypertrophy 3-4, strength 4-5, powerbuilding 3-5, endurance 2-3, general_fitness 3.\n"
    "8. Choose rest_seconds based on training type: hypertrophy 90, strength 180, powerbuilding 120, endurance 60, general_fitness 90.\n"
    "9. exerciseType MUST be one of: 'standard', 'superset', 'giant_set'. Do NOT use 'compound', 'isolation', or 'dropset' — dropsets are decided per-set during the workout, not at the programming stage.\n"
    "10. SUPERSET / GIANT SET PAIRING — CRITICAL:\n"
    "   - A superset pairs exactly 2 exercises performed back-to-back (e.g. biceps + triceps, quads + hams).\n"
    "   - A giant_set pairs 3+ exercises performed back-to-back (usually for arms or shoulders finishers).\n"
    "   - When you use exerciseType='superset' or 'giant_set', you MUST set supersetGroup (integer) on EVERY exercise in that group — all paired exercises get the SAME supersetGroup number.\n"
    "   - supersetGroup numbering starts at 1 within each day and increments per group. Exercises with exerciseType='standard' or 'dropset' MUST set supersetGroup to null.\n"
    "   - Pair exercises that make biomechanical sense (antagonistic pairs or synergistic same-muscle pairs). Don't superset two heavy compounds (e.g. squat + deadlift).\n"
    "   - Only use supersets/giant sets for intermediate/advanced users. Beginners: standard only.\n"
    "11. Use real, well-known exercise names (e.g. 'Barbell Bench Press', 'Romanian Deadlift', 'Lat Pulldown').\n"
    "12. displayOrder starts at 1 within each day and increments. Paired superset exercises get consecutive displayOrder values.\n"
    "You MUST respond with valid JSON in this exact format and NOTHING else:\n"
    '{"days": [{"day": "monday", "name": "Push Day", "description": "Chest, shoulders, triceps", "isRest": false, '
    '"exercises": ['
    '{"name": "Barbell Bench Press", "displayOrder": 1, "defaultSets": 4, "exerciseType": "standard", "supersetGroup": null, "restSeconds": 120, "notes": null}, '
    '{"name": "Incline Dumbbell Curl", "displayOrder": 4, "defaultSets": 3, "exerciseType": "superset", "supersetGroup": 1, "restSeconds": 60, "notes": null}, '
    '{"name": "Triceps Rope Pushdown", "displayOrder": 5, "defaultSets": 3, "exerciseType": "superset", "supersetGroup": 1, "restSeconds": 60, "notes": null}'
    ']}]}\n'
    "Do NOT include any text outside the JSON."
)


SPLIT_CUSTOMIZATION_SYSTEM_INSTRUCTION = (
    "You are an expert strength coach customizing a specific workout split for a user. "
    "The user wants to update ONE specific day of their training week. "
    "You will be given their current split for that day, their overall weekly split structure "
    "(to ensure balance), and their specific preferences or feedback. "
    "Rules:\n"
    "1. You MUST generate a replacement for the specific day requested.\n"
    "2. Use the user's preferences to guide exercise selection.\n"
    "3. Ensure the new exercises complement their other existing splits.\n"
    "4. Choose default sets and rest based on their training type (hypertrophy, strength, etc.).\n"
    "5. Use real, well-known exercise names.\n"
    "6. exerciseType MUST be one of: 'standard', 'superset', 'giant_set'. Do NOT use 'compound', 'isolation', or 'dropset' — dropsets are decided per-set during the workout, not at the programming stage.\n"
    "7. SUPERSET / GIANT SET PAIRING — CRITICAL:\n"
    "   - Superset = 2 exercises back-to-back. Giant set = 3+ exercises back-to-back.\n"
    "   - When you use exerciseType='superset' or 'giant_set', you MUST set supersetGroup (integer, starts at 1 for this day) on EVERY exercise in the group — all paired exercises share the SAME supersetGroup value.\n"
    "   - Exercises with exerciseType='standard' MUST set supersetGroup to null.\n"
    "   - Pair biomechanically-sensible exercises (antagonists or same-muscle accessories). Don't superset two heavy compounds.\n"
    "   - Paired exercises take consecutive displayOrder values.\n"
    "You MUST respond with valid JSON in this exact format and NOTHING else:\n"
    '{"day": "monday", "name": "Push Day", "description": "Chest, shoulders, triceps", "isRest": false, '
    '"exercises": ['
    '{"name": "Barbell Bench Press", "displayOrder": 1, "defaultSets": 4, "exerciseType": "standard", "supersetGroup": null, "restSeconds": 120, "notes": null}, '
    '{"name": "DB Biceps Curl", "displayOrder": 4, "defaultSets": 3, "exerciseType": "superset", "supersetGroup": 1, "restSeconds": 60, "notes": null}, '
    '{"name": "Triceps Rope Pushdown", "displayOrder": 5, "defaultSets": 3, "exerciseType": "superset", "supersetGroup": 1, "restSeconds": 60, "notes": null}'
    ']}\n'
    "Do NOT include any text outside the JSON."
)


def build_weekly_schedule_prompt(user, preferences: str | None = None) -> str:
    goal = user.goal.value if user.goal else "maintenance"
    training = user.training_type.value if user.training_type else "hypertrophy"
    experience = user.experience_level.value if getattr(user, "experience_level", None) else "beginner"
    activity = user.activity_level or "moderate"
    prompt = (
        f"Build a weekly workout split for this user.\n\n"
        f"Goal: {goal}\n"
        f"Training type: {training}\n"
        f"Experience level: {experience}\n"
        f"Activity level: {activity}\n"
        f"Age: {user.age}, Gender: {user.gender.value}, Weight: {user.weight}kg, Height: {user.height}cm\n\n"
    )

    if preferences:
        prompt += f"USER PREFERENCES / FEEDBACK:\n\"{preferences}\"\n\n"

    prompt += (
        f"Generate the full 7-day schedule (monday → sunday). Sunday must be rest "
        f"(or active walking recovery if goal is cutting). Return JSON only."
    )
    return prompt


def build_split_customization_prompt(
    user,
    all_splits: list,
    target_split,
    target_exercises: list,
    preferences: str | None = None
) -> str:
    """
    all_splits: list of WorkoutSplit objects (excluding target_split possibly, or all)
    target_split: the WorkoutSplit to customize
    target_exercises: list of SplitExercise objects for target_split
    """
    goal = user.goal.value if user.goal else "maintenance"
    training = user.training_type.value if user.training_type else "hypertrophy"
    experience = user.experience_level.value if getattr(user, "experience_level", None) else "beginner"

    context = (
        f"User: {_user_profile_line(user)}\n\n"
        f"=== OVERALL WEEKLY STRUCTURE ===\n"
    )
    for s in all_splits:
        context += f"- {s.day.capitalize()}: {s.name}"
        if s.id == target_split.id:
            context += " [TARGET FOR CUSTOMIZATION]"
        context += "\n"

    context += f"\n=== CURRENT PLAN FOR {target_split.day.upper()} ({target_split.name}) ===\n"
    if target_exercises:
        context += _format_split_exercises(target_exercises)
    else:
        context += "  (no exercises currently)\n"

    prompt = (
        f"{context}\n"
        f"Customize the {target_split.day} split based on the following feedback:\n"
    )

    if preferences:
        prompt += f"USER FEEDBACK: \"{preferences}\"\n\n"
    else:
        prompt += "Optimize the exercises for the user's goal and current experience level.\n\n"

    prompt += (
        f"Generate a replacement for the {target_split.day} split. "
        f"Return JSON only for this ONE day."
    )
    return prompt


SPLIT_ANALYSIS_SYSTEM_INSTRUCTION = (
    "You are a strength & hypertrophy coach answering a quick question about a user's weekly split.\n\n"

    "ANSWER STYLE:\n"
    "- Answer ONLY what the user asked. Do not audit the whole program.\n"
    "- Be direct: 2-4 short sentences in 'analysis'.\n"
    "- Include numbers only if they support the answer (e.g. weekly sets for the muscle asked about).\n"
    "- If the split is fine, say so — don't invent problems.\n"
    "- No preamble, no restating the question, no markdown.\n\n"

    "SCOPE:\n"
    "- Only use weekly set counts / frequency / recovery when the question needs them.\n"
    "- Assume rows hit biceps and presses hit triceps as indirect work.\n"
    "- Reference: hypertrophy weekly sets per muscle — beginner 8-12, intermediate 10-20, advanced 12-25.\n\n"

    "OUTPUT — strict JSON only:\n"
    '{"analysis": "2-4 sentences answering the question", '
    '"suggestions": ["1-3 concrete, short actions"]}\n'
    "Each suggestion is one line, under 15 words. Max 3 suggestions. If none are needed, return an empty array."
)


SESSION_COACH_SYSTEM_INSTRUCTION = (
    "You are a real-time gym coach embedded in a workout tracking app. "
    "The user is mid-session and asking you a quick question about their current workout. "
    "You have access to their split plan (exercises + target sets), current session logs, "
    "and their previous 4-5 sessions for the same split.\n\n"

    "DATA SHAPE NOTES:\n"
    "- Split plan exercises inside a '[Superset — perform back-to-back]' or '[Giant Set — perform back-to-back]' block are paired: user alternates sets between them with minimal rest.\n"
    "- A set marked '[TOP OF DROPSET]' is the heavy working set; '↘ drop:' lines under it are the lighter drops completed immediately after (no rest). Count drops toward fatigue/volume but NOT toward target set count.\n\n"

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
    "IMPORTANT: Pay attention to set notes (marked with '— note:') — they contain user feedback like "
    "unilateral imbalances, drop sets, grip issues, or form cues that should influence your recommendation. "
    "Consider the user's training style (hypertrophy, strength, etc.) and goal (bulking, cutting, maintenance) "
    "when recommending weights and rep ranges. "
    "CRITICAL:\n"
    "- If user is training at RIR ≤1 repeatedly → advise backing off slightly\n"
    "- If performance drops within session → reduce next set load\n"
    "- If user asks 'next weight' → give exact kg, not range\n"
    "- Always prioritize next set performance over ego lifting\n"
    "Respond in plain text, 2-4 sentences max. Be like a spotter who knows their history."
)


# ── prompt builders ──────────────────────────────────────────────────

def _format_split_exercises(split_exercises: list) -> str:
    """Render split exercises grouping superset/giant_set companions.

    Exercises sharing a superset_group are rendered together as a bracketed
    group so the LLM understands they're paired. `split_exercises` items are
    SplitExercise ORM objects or dicts with keys: name, default_sets,
    exercise_type, superset_group, rest_seconds, notes.
    """
    if not split_exercises:
        return "  (no exercises)\n"

    def _get(item, key, default=None):
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    groups: dict = {}
    standalone: list = []
    order_index: list = []
    for ex in split_exercises:
        ex_type = _get(ex, "exercise_type")
        if hasattr(ex_type, "value"):
            ex_type = ex_type.value
        ex_type = (ex_type or "standard").lower()
        group = _get(ex, "superset_group")
        if ex_type in ("superset", "giant_set") and group is not None:
            groups.setdefault(group, {"type": ex_type, "items": []})
            groups[group]["items"].append(ex)
            if group not in order_index:
                order_index.append(group)
        else:
            standalone.append(ex)

    lines: list[str] = []
    i = 1
    # Standalone first in display_order, then groups.  Preserve natural order
    # as best as we can: interleave standalones and groups by the first
    # member's display_order if available.
    def _display_order(item):
        return _get(item, "display_order", 999)

    # Build combined ordered list of "entries": either a single exercise or a group
    entries: list = []
    consumed_groups: set = set()
    all_items = list(split_exercises)
    for ex in all_items:
        ex_type = _get(ex, "exercise_type")
        if hasattr(ex_type, "value"):
            ex_type = ex_type.value
        ex_type = (ex_type or "standard").lower()
        group = _get(ex, "superset_group")
        if ex_type in ("superset", "giant_set") and group is not None:
            if group in consumed_groups:
                continue
            consumed_groups.add(group)
            entries.append(("group", group, groups[group]))
        else:
            entries.append(("solo", None, ex))

    for entry in entries:
        kind = entry[0]
        if kind == "solo":
            ex = entry[2]
            line = (
                f"  {i}. {_get(ex, 'name') or 'Exercise'} — "
                f"{_get(ex, 'default_sets', 3)} sets, "
                f"{_get(ex, 'rest_seconds', 90)}s rest"
            )
            if _get(ex, "notes"):
                line += f" (notes: {_get(ex, 'notes')})"
            lines.append(line)
            i += 1
        else:
            g = entry[2]
            label = "Superset" if g["type"] == "superset" else "Giant Set"
            items = g["items"]
            lines.append(f"  {i}. [{label} — perform back-to-back]:")
            for j, ex in enumerate(items, 1):
                line = (
                    f"     {chr(ord('a') + j - 1)}. {_get(ex, 'name') or 'Exercise'} — "
                    f"{_get(ex, 'default_sets', 3)} sets, "
                    f"{_get(ex, 'rest_seconds', 90)}s rest"
                )
                if _get(ex, "notes"):
                    line += f" (notes: {_get(ex, 'notes')})"
                lines.append(line)
            i += 1

    return "\n".join(lines) + "\n"


def _format_session_sets(sets: list) -> list[str]:
    """Render logged sets grouped into dropset chains.

    Top sets render on one line; their drops render indented below.
    `sets` items are ExerciseSet ORM objects (order by set_number).
    Returns a list of lines (no trailing newline).
    """
    by_id = {s.id: s for s in sets}
    children: dict = {}
    for s in sets:
        if s.parent_set_id and s.parent_set_id in by_id:
            children.setdefault(s.parent_set_id, []).append(s)

    lines: list[str] = []
    for s in sorted(sets, key=lambda x: x.set_number):
        # Skip drops here — they're rendered under their parent.
        if s.parent_set_id and s.parent_set_id in by_id:
            continue
        warmup = " [WARMUP]" if s.is_warmup else ""
        rir = f", RIR {s.reps_in_reserve}" if s.reps_in_reserve is not None else ""
        desc = f" — note: {s.description}" if s.description else ""
        dropset_marker = " [TOP OF DROPSET]" if children.get(s.id) else ""
        lines.append(
            f"  Set {s.set_number}: {s.weight_kg}kg x {s.reps}{rir}{warmup}{dropset_marker}{desc}"
        )
        for drop in sorted(children.get(s.id, []), key=lambda x: x.set_number):
            d_rir = (
                f", RIR {drop.reps_in_reserve}"
                if drop.reps_in_reserve is not None
                else ""
            )
            d_desc = f" — note: {drop.description}" if drop.description else ""
            lines.append(
                f"    ↘ drop: {drop.weight_kg}kg x {drop.reps}{d_rir}{d_desc}"
            )
    return lines


def _user_profile_line(user) -> str:
    """Compact one-line user profile for prompts."""
    training = user.training_type.value if getattr(user, "training_type", None) else "hypertrophy"
    experience = user.experience_level.value if getattr(user, "experience_level", None) else "beginner"
    activity = getattr(user, "activity_level", None) or "unspecified"
    return (
        f"Goal = {user.goal.value}, Training type = {training}, "
        f"Experience = {experience}, Activity = {activity}, "
        f"Weight = {user.weight}kg, Height = {user.height}cm, "
        f"Age = {user.age}, Gender = {user.gender.value}"
    )


def build_session_analysis_prompt(
    user,
    sessions: list[dict],
    question: str | None = None,
) -> str:
    context = (
        f"User profile: {_user_profile_line(user)}\n\n"
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
        "Analyze this workout data. Focus on:\n"
        "1. Real progression (are reps/strength improving?)\n"
        "2. Fatigue accumulation (RIR trends, long sessions, performance drops)\n"
        "3. Effective vs junk volume\n"
        "4. Session efficiency (is time spent productive?)\n"
        "5. Whether intensity distribution is optimal (not just high)\n"
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
        f"User profile: {_user_profile_line(user)}\n\n"
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
        "Analyze this exercise progression data. Focus on:\n"
        "1. Strength trend (clear increase, plateau, or regression)\n"
        "2. Rep quality vs fatigue (low RIR but no progression = red flag)\n"
        "3. Whether load progression is too aggressive or too conservative\n"
        "4. Identify exact plateau points (specific sessions)\n"
        "5. Provide a FIXED progression strategy (not generic advice)\n"
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
        f"User profile: {_user_profile_line(user)}\n\n"
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

    # Include individual log entries with body metrics and user notes
    detailed = analytics.get("detailed_entries", [])
    if detailed:
        context += "\nDetailed log entries:\n"
        for entry in detailed:
            line = f"- {entry['date']}: {entry['weight_kg']}kg"
            if "waist_cm" in entry:
                line += f", waist {entry['waist_cm']}cm"
            if "body_fat_pct" in entry:
                line += f", body fat {entry['body_fat_pct']}%"
            if "note" in entry:
                line += f" — note: {entry['note']}"
            context += line + "\n"

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

    prompt += (
        "IMPORTANT: Pay attention to any user notes on log entries — they contain context like "
        "missed meals, cheat days, water retention, illness, etc. that explain weight fluctuations "
        "and should inform your analysis.\n"
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
        f"User profile: Name = {user.first_name}, {_user_profile_line(user)}\n\n"
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
    # Split plan context (target exercises) — grouped by superset
    split_ctx = ""
    if split_exercises:
        split_ctx = (
            "=== SPLIT PLAN (target exercises & sets for this session) ===\n"
            + _format_split_exercises(split_exercises)
            + "\n"
        )

    # Build a map of exercise name -> target sets from split plan
    target_sets_map = {}
    if split_exercises:
        for se in split_exercises:
            target_sets_map[se.name.lower()] = se.default_sets

    # Current session: drops do NOT count toward completion.
    current_ctx = "=== CURRENT SESSION (in progress) ===\n"
    for ex in session.exercises:
        completed_sets = len(
            [s for s in ex.sets if not s.is_warmup and s.parent_set_id is None]
        )
        target = target_sets_map.get(ex.exercise_name.lower(), "?")
        status = (
            "DONE"
            if target != "?" and completed_sets >= target
            else f"{completed_sets}/{target} sets done"
        )
        current_ctx += f"\n{ex.exercise_name} [{status}]:\n"
        if not ex.sets:
            current_ctx += "  (no sets logged yet)\n"
            continue
        for line in _format_session_sets(ex.sets):
            current_ctx += line + "\n"

    # History context — drop chains rendered under parent
    history_ctx = (
        f"\n=== PREVIOUS SESSIONS (same split, last {len(past_sessions)} sessions) ===\n"
    )
    for ps in past_sessions:
        ps_date = ps.started_at.strftime("%a, %b %d") if ps.started_at else "?"
        history_ctx += f"\n--- {ps_date} ---\n"
        for ex in ps.exercises:
            history_ctx += f"{ex.exercise_name}:\n"
            for line in _format_session_sets(ex.sets):
                history_ctx += line + "\n"

    return (
        f"User: {_user_profile_line(user)}\n\n"
        f"{split_ctx}{current_ctx}\n{history_ctx}\n"
        f"User's question: {question}"
    )


def build_split_analysis_prompt(
    user,
    splits_with_exercises: list[dict],
    current_weight_kg: float | None,
    question: str,
) -> str:
    weight_source = "latest weight log" if current_weight_kg is not None else "profile"
    weight_value = current_weight_kg if current_weight_kg is not None else user.weight

    context = (
        f"User profile: {_user_profile_line(user)}\n"
        f"Current body weight ({weight_source}): {weight_value}kg\n\n"
        f"=== WEEKLY SPLIT ===\n"
    )

    days_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_index = {d: i for i, d in enumerate(days_order)}
    sorted_splits = sorted(
        splits_with_exercises,
        key=lambda s: day_index.get(str(s.get("day", "")).lower(), 99),
    )

    if not sorted_splits:
        context += "(no splits configured)\n"
    else:
        for split in sorted_splits:
            day = str(split.get("day", "")).capitalize()
            name = split.get("name") or ""
            context += f"\n{day} — {name}"
            if split.get("description"):
                context += f" ({split['description']})"
            context += "\n"
            exercises = split.get("exercises") or []
            if not exercises:
                context += "  (rest day / no exercises)\n"
                continue
            context += _format_split_exercises(exercises)

    prompt = (
        f"{context}\n"
        f"User's question:\n\"{question}\"\n\n"
        f"Answer only this question. 2-4 sentences. Cite numbers only if they bear directly on the "
        f"answer (treat direct sets as 1.0, indirect as 0.5). Skip anything the user didn't ask about."
    )
    return prompt


def build_session_plan_prompt(
    user,
    split_exercises: list,
    past_sessions: list,
) -> str:
    # Split plan — supersets/giant sets grouped so the AI pairs reps correctly
    plan_ctx = "=== TODAY'S SPLIT PLAN ===\n" + _format_split_exercises(split_exercises)

    # Past sessions with dates (including gaps), dropset chains rendered
    history_ctx = ""
    if past_sessions:
        history_ctx = f"\n=== PREVIOUS SESSIONS ({len(past_sessions)} sessions, most recent first) ===\n"
        for ps in past_sessions:
            ps_date = ps.started_at.strftime("%Y-%m-%d (%a)") if ps.started_at else "?"
            history_ctx += f"\n--- {ps_date} ---\n"
            for ex in ps.exercises:
                history_ctx += f"{ex.exercise_name}:\n"
                for line in _format_session_sets(ex.sets):
                    history_ctx += line + "\n"
    else:
        history_ctx = "\n=== NO PREVIOUS SESSIONS FOUND ===\nThis is the user's first time doing this split. Suggest conservative starting weights.\n"

    training = user.training_type.value if hasattr(user, 'training_type') and user.training_type else "hypertrophy"
    experience = user.experience_level.value if getattr(user, "experience_level", None) else "beginner"
    return (
        f"User: {_user_profile_line(user)}\n"
        f"Today's date: {__import__('datetime').date.today().strftime('%Y-%m-%d (%A)')}\n\n"
        f"{plan_ctx}\n{history_ctx}\n"
        f"Generate a complete recommended session plan with specific weights and reps for EVERY exercise in the split plan. "
        f"Follow the exercise order from the split plan. "
        f"Include warmup sets for the first 1-2 compound exercises. "
        f"The user's training style is {training} — adjust rep ranges accordingly "
        f"(hypertrophy: 8-12 reps, strength: 3-6 reps, powerbuilding: mix of both, endurance: 12-20 reps, general_fitness: 8-15 reps). "
        f"Experience level is {experience} — for beginners use very conservative starting weights and add more warmup sets; "
        f"for advanced users be more aggressive with progressive overload."
    )
