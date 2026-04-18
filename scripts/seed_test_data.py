"""
Seed script: creates 3 test users with realistic 3-4 month workout & body logs.

Users:
  1. Alex (Bulking + Hypertrophy)  - Push/Pull/Legs x2, Sun rest
  2. Priya (Cutting + Hypertrophy) - Upper/Lower x2 + Full Body, Sun rest
  3. Marcus (Bulking + Strength)   - SBD + accessories, Sun rest

Run:  python -m scripts.seed_test_data
Skip: existing users detected by email are skipped automatically.
"""

import asyncio, uuid
import random
import sys
import os
from datetime import date, datetime, timedelta, timezone

# allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.database import AsyncSessionLocal, engine
from db.base import Base
from db.uuid import new_uuid
import db.init_models  # noqa – register models

from features.users.users_model import User
from features.users.users_enum import GoalEnum, GenderEnum, TrainingTypeEnum, ExperienceLevelEnum
from features.workout_split.workout_split_model import WorkoutSplit
from features.workout_split.workout_split_enum import DayEnum
from features.split_exercise.split_exercise_model import SplitExercise
from features.split_exercise.split_exercise_enum import ExerciseTypeEnum
from features.workout_session.workout_session_model import WorkoutSession
from features.workout_session.workout_session_enum import SessionStatusEnum
from features.workout_session.session_exercise_model import SessionExercise
from features.exercise_set.exercise_set_model import ExerciseSet
from features.weight_log.weight_log_model import WeightLog
from core.security import hash_password

random.seed(42)

# ── date range ────────────────────────────────────────────────────────────────
SEED_START = date(2026, 1, 1)
SEED_END = date(2026, 4, 8)
DAY_MAP = {
    0: DayEnum.MONDAY,
    1: DayEnum.TUESDAY,
    2: DayEnum.WEDNESDAY,
    3: DayEnum.THURSDAY,
    4: DayEnum.FRIDAY,
    5: DayEnum.SATURDAY,
    6: DayEnum.SUNDAY,
}

# ── user profiles ─────────────────────────────────────────────────────────────
USERS = [
    {
        "first_name": "Alex",
        "last_name": "Thompson",
        "email": "alex.test@progressionx.dev",
        "password": "Test@1234",
        "age": 25,
        "weight": 75.0,
        "height": 178,
        "goal": GoalEnum.BULKING,
        "gender": GenderEnum.MALE,
        "training_type": TrainingTypeEnum.HYPERTROPHY,
        "experience_level": ExperienceLevelEnum.INTERMEDIATE,
        "activity_level": "moderately_active",
    },
    {
        "first_name": "Priya",
        "last_name": "Sharma",
        "email": "priya.test@progressionx.dev",
        "password": "Test@1234",
        "age": 28,
        "weight": 62.0,
        "height": 163,
        "goal": GoalEnum.CUTTING,
        "gender": GenderEnum.FEMALE,
        "training_type": TrainingTypeEnum.HYPERTROPHY,
        "experience_level": ExperienceLevelEnum.BEGINNER,
        "activity_level": "very_active",
    },
    {
        "first_name": "Marcus",
        "last_name": "Reed",
        "email": "marcus.test@progressionx.dev",
        "password": "Test@1234",
        "age": 30,
        "weight": 90.0,
        "height": 185,
        "goal": GoalEnum.BULKING,
        "gender": GenderEnum.MALE,
        "training_type": TrainingTypeEnum.STRENGTH,
        "experience_level": ExperienceLevelEnum.ADVANCED,
        "activity_level": "very_active",
    },
]

# ── split templates (Sun = rest for all) ──────────────────────────────────────

# Alex – Push / Pull / Legs x2
ALEX_SPLITS = {
    DayEnum.MONDAY: {
        "name": "Push A",
        "exercises": [
            ("Barbell Bench Press", 4, 90),
            ("Incline Dumbbell Press", 3, 75),
            ("Cable Flyes", 3, 60),
            ("Overhead Press", 3, 90),
            ("Lateral Raises", 3, 45),
            ("Tricep Pushdowns", 3, 60),
        ],
    },
    DayEnum.TUESDAY: {
        "name": "Pull A",
        "exercises": [
            ("Barbell Rows", 4, 90),
            ("Lat Pulldowns", 3, 75),
            ("Cable Rows", 3, 75),
            ("Face Pulls", 3, 45),
            ("Barbell Curls", 3, 60),
            ("Hammer Curls", 3, 45),
        ],
    },
    DayEnum.WEDNESDAY: {
        "name": "Legs A",
        "exercises": [
            ("Barbell Squat", 4, 120),
            ("Romanian Deadlift", 3, 90),
            ("Leg Press", 3, 90),
            ("Leg Curls", 3, 60),
            ("Calf Raises", 4, 45),
        ],
    },
    DayEnum.THURSDAY: {
        "name": "Push B",
        "exercises": [
            ("Dumbbell Bench Press", 4, 75),
            ("Machine Chest Press", 3, 60),
            ("Pec Deck", 3, 45),
            ("Arnold Press", 3, 75),
            ("Cable Lateral Raises", 3, 45),
            ("Overhead Tricep Extension", 3, 60),
        ],
    },
    DayEnum.FRIDAY: {
        "name": "Pull B",
        "exercises": [
            ("Pull Ups", 4, 90),
            ("T-Bar Rows", 3, 90),
            ("Single Arm Dumbbell Row", 3, 75),
            ("Rear Delt Flyes", 3, 45),
            ("Preacher Curls", 3, 60),
            ("Incline Dumbbell Curls", 3, 45),
        ],
    },
    DayEnum.SATURDAY: {
        "name": "Legs B",
        "exercises": [
            ("Front Squat", 4, 120),
            ("Bulgarian Split Squat", 3, 75),
            ("Leg Extensions", 3, 60),
            ("Seated Leg Curls", 3, 60),
            ("Standing Calf Raises", 4, 45),
        ],
    },
}

# Priya – Upper/Lower x2 + Full Body (cutting)
PRIYA_SPLITS = {
    DayEnum.MONDAY: {
        "name": "Upper A",
        "exercises": [
            ("Dumbbell Bench Press", 3, 75),
            ("Seated Cable Row", 3, 75),
            ("Shoulder Press Machine", 3, 60),
            ("Lat Pulldowns", 3, 75),
            ("Lateral Raises", 3, 45),
            ("Tricep Rope Pushdowns", 3, 45),
            ("Dumbbell Curls", 3, 45),
        ],
    },
    DayEnum.TUESDAY: {
        "name": "Lower A",
        "exercises": [
            ("Barbell Squat", 4, 90),
            ("Romanian Deadlift", 3, 90),
            ("Hip Thrust", 3, 75),
            ("Walking Lunges", 3, 60),
            ("Leg Curls", 3, 60),
            ("Calf Raises", 3, 45),
        ],
    },
    DayEnum.WEDNESDAY: {
        "name": "Active Recovery",
        "exercises": [
            ("Incline Walk (Treadmill)", 1, 0),
            ("Band Pull Aparts", 3, 30),
            ("Plank Hold", 3, 30),
            ("Hip Flexor Stretch", 2, 30),
        ],
    },
    DayEnum.THURSDAY: {
        "name": "Upper B",
        "exercises": [
            ("Incline Dumbbell Press", 3, 75),
            ("Barbell Rows", 3, 90),
            ("Overhead Press", 3, 75),
            ("Cable Flyes", 3, 60),
            ("Face Pulls", 3, 45),
            ("EZ Bar Curls", 3, 45),
            ("Skull Crushers", 3, 60),
        ],
    },
    DayEnum.FRIDAY: {
        "name": "Lower B",
        "exercises": [
            ("Leg Press", 4, 90),
            ("Sumo Deadlift", 3, 90),
            ("Bulgarian Split Squat", 3, 60),
            ("Leg Extensions", 3, 60),
            ("Seated Leg Curls", 3, 60),
            ("Standing Calf Raises", 3, 45),
        ],
    },
    DayEnum.SATURDAY: {
        "name": "Full Body",
        "exercises": [
            ("Deadlift", 3, 120),
            ("Dumbbell Bench Press", 3, 75),
            ("Pull Ups", 3, 90),
            ("Goblet Squat", 3, 60),
            ("Cable Lateral Raises", 3, 45),
        ],
    },
}

# Marcus – Strength (SBD focused)
MARCUS_SPLITS = {
    DayEnum.MONDAY: {
        "name": "Heavy Squat",
        "exercises": [
            ("Barbell Squat", 5, 180),
            ("Pause Squat", 3, 150),
            ("Leg Press", 3, 120),
            ("Barbell Good Mornings", 3, 90),
            ("Ab Wheel Rollouts", 3, 60),
        ],
    },
    DayEnum.TUESDAY: {
        "name": "Heavy Bench",
        "exercises": [
            ("Barbell Bench Press", 5, 180),
            ("Close Grip Bench Press", 3, 120),
            ("Incline Barbell Press", 3, 120),
            ("Weighted Dips", 3, 90),
            ("Tricep Pushdowns", 3, 60),
        ],
    },
    DayEnum.WEDNESDAY: {
        "name": "Heavy Deadlift",
        "exercises": [
            ("Conventional Deadlift", 5, 180),
            ("Deficit Deadlift", 3, 150),
            ("Barbell Rows", 4, 120),
            ("Pull Ups", 3, 90),
            ("Barbell Shrugs", 3, 90),
        ],
    },
    DayEnum.THURSDAY: {
        "name": "Volume Squat & Accessories",
        "exercises": [
            ("Barbell Squat", 4, 150),
            ("Front Squat", 3, 120),
            ("Leg Extensions", 3, 60),
            ("Leg Curls", 3, 60),
            ("Calf Raises", 4, 45),
        ],
    },
    DayEnum.FRIDAY: {
        "name": "Volume Bench & Shoulders",
        "exercises": [
            ("Barbell Bench Press", 4, 150),
            ("Overhead Press", 4, 120),
            ("Dumbbell Bench Press", 3, 90),
            ("Lateral Raises", 3, 45),
            ("Face Pulls", 3, 45),
        ],
    },
    DayEnum.SATURDAY: {
        "name": "Back & Arms",
        "exercises": [
            ("Pendlay Rows", 4, 120),
            ("Weighted Pull Ups", 3, 120),
            ("Cable Rows", 3, 90),
            ("Barbell Curls", 3, 60),
            ("Skull Crushers", 3, 60),
        ],
    },
}

SPLIT_MAP = [ALEX_SPLITS, PRIYA_SPLITS, MARCUS_SPLITS]

# ── realistic base weights per exercise (kg) ─────────────────────────────────
# Format: (base_weight, rep_range_low, rep_range_high)
# These vary by user profile; we scale by user index.

def _base_weights(user_idx: int):
    """Return dict of exercise_name -> (base_kg, rep_lo, rep_hi) per user."""
    # user 0 = Alex (hypertrophy bulking, moderate weights, 8-12 reps)
    # user 1 = Priya (hypertrophy cutting, lighter, 10-15 reps)
    # user 2 = Marcus (strength bulking, heavy, 3-6 reps main, 6-10 accessories)
    profiles = {
        0: {  # Alex – hypertrophy
            "Barbell Bench Press": (70, 8, 12), "Incline Dumbbell Press": (26, 8, 12),
            "Cable Flyes": (15, 10, 15), "Overhead Press": (40, 8, 12),
            "Lateral Raises": (10, 12, 15), "Tricep Pushdowns": (25, 10, 15),
            "Barbell Rows": (60, 8, 12), "Lat Pulldowns": (55, 8, 12),
            "Cable Rows": (50, 10, 12), "Face Pulls": (20, 12, 15),
            "Barbell Curls": (30, 8, 12), "Hammer Curls": (14, 10, 12),
            "Barbell Squat": (80, 6, 10), "Romanian Deadlift": (70, 8, 12),
            "Leg Press": (140, 8, 12), "Leg Curls": (40, 10, 12),
            "Calf Raises": (60, 12, 18),
            "Dumbbell Bench Press": (30, 8, 12), "Machine Chest Press": (50, 10, 12),
            "Pec Deck": (40, 10, 15), "Arnold Press": (20, 8, 12),
            "Cable Lateral Raises": (8, 12, 15), "Overhead Tricep Extension": (22, 10, 12),
            "Pull Ups": (0, 6, 10), "T-Bar Rows": (50, 8, 12),
            "Single Arm Dumbbell Row": (28, 8, 12), "Rear Delt Flyes": (10, 12, 15),
            "Preacher Curls": (25, 8, 12), "Incline Dumbbell Curls": (12, 10, 12),
            "Front Squat": (60, 6, 10), "Bulgarian Split Squat": (16, 8, 12),
            "Leg Extensions": (45, 10, 15), "Seated Leg Curls": (38, 10, 12),
            "Standing Calf Raises": (70, 12, 18),
        },
        1: {  # Priya – hypertrophy cutting (lighter)
            "Dumbbell Bench Press": (14, 10, 15), "Seated Cable Row": (35, 10, 15),
            "Shoulder Press Machine": (20, 10, 15), "Lat Pulldowns": (35, 10, 15),
            "Lateral Raises": (6, 12, 15), "Tricep Rope Pushdowns": (15, 12, 15),
            "Dumbbell Curls": (8, 10, 15),
            "Barbell Squat": (45, 8, 12), "Romanian Deadlift": (40, 10, 12),
            "Hip Thrust": (60, 8, 12), "Walking Lunges": (12, 10, 14),
            "Leg Curls": (25, 10, 15), "Calf Raises": (35, 12, 18),
            "Incline Walk (Treadmill)": (0, 1, 1), "Band Pull Aparts": (0, 15, 20),
            "Plank Hold": (0, 1, 1), "Hip Flexor Stretch": (0, 1, 1),
            "Incline Dumbbell Press": (12, 10, 15), "Barbell Rows": (35, 10, 12),
            "Overhead Press": (22, 10, 12), "Cable Flyes": (10, 12, 15),
            "Face Pulls": (12, 12, 15), "EZ Bar Curls": (15, 10, 15),
            "Skull Crushers": (12, 10, 15),
            "Leg Press": (90, 10, 15), "Sumo Deadlift": (50, 8, 12),
            "Bulgarian Split Squat": (10, 10, 14), "Leg Extensions": (30, 12, 15),
            "Seated Leg Curls": (22, 10, 15), "Standing Calf Raises": (40, 12, 18),
            "Deadlift": (55, 6, 10), "Pull Ups": (0, 4, 8),
            "Goblet Squat": (16, 10, 14), "Cable Lateral Raises": (5, 12, 15),
        },
        2: {  # Marcus – strength (heavy, lower reps for compounds)
            "Barbell Squat": (140, 3, 6), "Pause Squat": (110, 3, 5),
            "Leg Press": (200, 6, 10), "Barbell Good Mornings": (60, 6, 10),
            "Ab Wheel Rollouts": (0, 8, 12),
            "Barbell Bench Press": (120, 3, 6), "Close Grip Bench Press": (95, 5, 8),
            "Incline Barbell Press": (85, 5, 8), "Weighted Dips": (30, 5, 8),
            "Tricep Pushdowns": (35, 8, 12),
            "Conventional Deadlift": (170, 2, 5), "Deficit Deadlift": (140, 3, 5),
            "Barbell Rows": (90, 5, 8), "Pull Ups": (20, 5, 8),
            "Barbell Shrugs": (100, 6, 10),
            "Front Squat": (100, 4, 6), "Leg Extensions": (60, 8, 12),
            "Leg Curls": (45, 8, 12), "Calf Raises": (80, 10, 15),
            "Overhead Press": (70, 4, 6), "Dumbbell Bench Press": (38, 6, 10),
            "Lateral Raises": (14, 10, 15), "Face Pulls": (22, 10, 15),
            "Pendlay Rows": (85, 4, 6), "Weighted Pull Ups": (25, 4, 6),
            "Cable Rows": (65, 6, 10), "Barbell Curls": (35, 6, 10),
            "Skull Crushers": (28, 6, 10),
        },
    }
    return profiles[user_idx]


# ── helper: progressive overload with noise ───────────────────────────────────

def _progress_weight(base: float, week: int, total_weeks: int, user_idx: int) -> float:
    """Slowly increase weight over weeks with some noise."""
    if base == 0:
        return 0.0
    # total gain over period
    if user_idx == 0:
        gain_pct = 0.12  # Alex gains ~12% over period
    elif user_idx == 1:
        gain_pct = 0.05  # Priya maintains/slight gain while cutting
    else:
        gain_pct = 0.08  # Marcus gains ~8% on strength lifts
    linear = base * (1 + gain_pct * (week / max(total_weeks, 1)))
    noise = random.uniform(-0.02, 0.02) * base
    return round(max(linear + noise, base * 0.9), 1)


def _vary_reps(lo: int, hi: int) -> int:
    return random.randint(lo, hi)


# ── weight / body log generators ──────────────────────────────────────────────

def _weight_logs_alex(user_id: uuid.UUID) -> list[WeightLog]:
    """Bulking: 75 kg -> ~80 kg over 14 weeks, logs every 3-4 days."""
    logs = []
    d = SEED_START
    w = 75.0
    while d <= SEED_END:
        w += random.uniform(0.05, 0.2)
        noise = random.uniform(-0.3, 0.3)
        waist = 82.0 + (w - 75.0) * 0.4 + random.uniform(-0.5, 0.5)
        bf = 14.0 + (w - 75.0) * 0.25 + random.uniform(-0.3, 0.3)
        logs.append(WeightLog(
            id=new_uuid(), user_id=user_id,
            weight_kg=round(w + noise, 1),
            waist_cm=round(waist, 1),
            body_fat_pct=round(bf, 1),
            logged_at=d,
        ))
        d += timedelta(days=random.choice([3, 4]))
    return logs


def _weight_logs_priya(user_id: uuid.UUID) -> list[WeightLog]:
    """Cutting: 62 kg -> ~56 kg over 14 weeks, logs every 2-3 days."""
    logs = []
    d = SEED_START
    w = 62.0
    while d <= SEED_END:
        w -= random.uniform(0.08, 0.22)
        noise = random.uniform(-0.4, 0.4)
        waist = 72.0 - (62.0 - w) * 0.6 + random.uniform(-0.5, 0.5)
        bf = 26.0 - (62.0 - w) * 0.9 + random.uniform(-0.3, 0.3)
        logs.append(WeightLog(
            id=new_uuid(), user_id=user_id,
            weight_kg=round(w + noise, 1),
            waist_cm=round(waist, 1),
            body_fat_pct=round(bf, 1),
            logged_at=d,
        ))
        d += timedelta(days=random.choice([2, 3]))
    return logs


def _weight_logs_marcus(user_id: uuid.UUID) -> list[WeightLog]:
    """Bulking strength: 90 kg -> ~96 kg over 14 weeks, logs weekly."""
    logs = []
    d = SEED_START
    w = 90.0
    while d <= SEED_END:
        w += random.uniform(0.2, 0.6)
        noise = random.uniform(-0.3, 0.3)
        waist = 88.0 + (w - 90.0) * 0.35 + random.uniform(-0.5, 0.5)
        bf = 17.0 + (w - 90.0) * 0.15 + random.uniform(-0.3, 0.3)
        logs.append(WeightLog(
            id=new_uuid(), user_id=user_id,
            weight_kg=round(w + noise, 1),
            waist_cm=round(waist, 1),
            body_fat_pct=round(bf, 1),
            logged_at=d,
        ))
        d += timedelta(days=random.choice([6, 7, 8]))
    return logs


WEIGHT_LOG_FNS = [_weight_logs_alex, _weight_logs_priya, _weight_logs_marcus]

# ── main seed logic ───────────────────────────────────────────────────────────

async def seed():
    async with AsyncSessionLocal() as session:
        total_weeks = (SEED_END - SEED_START).days // 7

        for user_idx, profile in enumerate(USERS):
            # ── check if user exists ──
            existing = (await session.execute(
                select(User).where(User.email == profile["email"])
            )).scalar_one_or_none()

            if existing:
                print(f"[SKIP] User '{profile['email']}' already exists.")
                continue

            print(f"\n{'='*60}")
            print(f"[CREATE] User: {profile['first_name']} {profile['last_name']} "
                  f"({profile['goal'].value} / {profile['training_type'].value})")
            print(f"{'='*60}")

            # ── create user ──
            user = User(
                id=new_uuid(),
                first_name=profile["first_name"],
                last_name=profile["last_name"],
                email=profile["email"],
                hashed_password=hash_password(profile["password"]),
                age=profile["age"],
                weight=profile["weight"],
                height=profile["height"],
                goal=profile["goal"],
                gender=profile["gender"],
                training_type=profile["training_type"],
                experience_level=profile["experience_level"],
                activity_level=profile["activity_level"],
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"  -> User created (id={user.id})")

            # ── create splits & exercises ──
            split_template = SPLIT_MAP[user_idx]
            splits_by_day: dict[DayEnum, WorkoutSplit] = {}
            split_exercises_by_day: dict[DayEnum, list[SplitExercise]] = {}

            for day_enum, split_def in split_template.items():
                split = WorkoutSplit(
                    id=new_uuid(),
                    user_id=user.id,
                    name=split_def["name"],
                    day=day_enum,
                    description=f"{profile['first_name']}'s {split_def['name']} day",
                )
                session.add(split)
                await session.flush()
                splits_by_day[day_enum] = split

                exercises = []
                for order, (ex_name, default_sets, rest_sec) in enumerate(
                    split_def["exercises"], start=1
                ):
                    se = SplitExercise(
                        id=new_uuid(),
                        split_id=split.id,
                        name=ex_name,
                        display_order=order,
                        default_sets=default_sets,
                        exercise_type=ExerciseTypeEnum.STANDARD,
                        rest_seconds=rest_sec,
                    )
                    session.add(se)
                    exercises.append(se)
                await session.flush()
                split_exercises_by_day[day_enum] = exercises

            print(f"  -> {len(splits_by_day)} splits created (Sun = rest)")

            # ── generate workout sessions day by day ──
            base_weights = _base_weights(user_idx)
            session_count = 0
            set_count = 0
            current = SEED_START

            while current <= SEED_END:
                weekday = current.weekday()
                day_enum = DAY_MAP[weekday]

                # Sunday = rest
                if day_enum == DayEnum.SUNDAY:
                    current += timedelta(days=1)
                    continue

                # skip if no split for this day
                if day_enum not in splits_by_day:
                    current += timedelta(days=1)
                    continue

                # randomly skip ~12% of days (sick, busy, travel)
                if random.random() < 0.12:
                    current += timedelta(days=1)
                    continue

                split = splits_by_day[day_enum]
                split_exs = split_exercises_by_day[day_enum]
                week_num = (current - SEED_START).days // 7

                # session time: 6-9 AM or 5-8 PM
                if random.random() < 0.6:
                    hour = random.randint(6, 8)
                else:
                    hour = random.randint(17, 19)
                minute = random.randint(0, 59)
                started_at = datetime(
                    current.year, current.month, current.day,
                    hour, minute, 0, tzinfo=timezone.utc
                )

                duration = random.randint(50, 95) * 60  # 50-95 min
                completed_at = started_at + timedelta(seconds=duration)

                # occasional abandoned session (~3%)
                is_abandoned = random.random() < 0.03
                status = SessionStatusEnum.ABANDONED if is_abandoned else SessionStatusEnum.COMPLETED

                notes = None
                if random.random() < 0.15:
                    note_options = [
                        "Felt strong today", "Low energy, pushed through",
                        "Great pump", "Slightly sore from yesterday",
                        "PR attempt", "Deload week – lighter weights",
                        "Quick session, time-crunched", "Solid session overall",
                        "Shoulder felt tight during presses",
                        "Good mind-muscle connection today",
                    ]
                    notes = random.choice(note_options)

                ws = WorkoutSession(
                    id=new_uuid(),
                    user_id=user.id,
                    split_id=split.id,
                    started_at=started_at,
                    completed_at=None if is_abandoned else completed_at,
                    duration_seconds=None if is_abandoned else duration,
                    status=status,
                    notes=notes,
                )
                session.add(ws)
                await session.flush()
                session_count += 1

                # ── exercises & sets ──
                # if abandoned, only do first 1-2 exercises
                ex_limit = random.randint(1, 2) if is_abandoned else len(split_exs)

                for ex_order, split_ex in enumerate(split_exs[:ex_limit], start=1):
                    se = SessionExercise(
                        id=new_uuid(),
                        session_id=ws.id,
                        split_exercise_id=split_ex.id,
                        exercise_name=split_ex.name,
                        display_order=ex_order,
                        exercise_type=split_ex.exercise_type,
                    )
                    session.add(se)
                    await session.flush()

                    bw = base_weights.get(split_ex.name, (20, 8, 12))
                    base_kg, rep_lo, rep_hi = bw

                    # deload every 4th week
                    is_deload = (week_num % 4 == 3)
                    num_sets = split_ex.default_sets

                    for s_num in range(1, num_sets + 1):
                        w = _progress_weight(base_kg, week_num, total_weeks, user_idx)
                        if is_deload:
                            w = round(w * 0.7, 1)
                        # slight drop on last sets (fatigue)
                        if s_num >= 3 and random.random() < 0.3:
                            w = round(w * 0.95, 1)

                        reps = _vary_reps(rep_lo, rep_hi)
                        if is_deload:
                            reps = min(reps + 2, rep_hi + 3)
                        # last set: sometimes fewer reps (failure)
                        if s_num == num_sets and random.random() < 0.25:
                            reps = max(reps - random.randint(1, 3), 1)

                        rir = None
                        if not is_deload and random.random() < 0.7:
                            if s_num == num_sets:
                                rir = random.choice([0, 0, 1, 1, 2])
                            else:
                                rir = random.choice([1, 2, 2, 3, 3])

                        es = ExerciseSet(
                            id=new_uuid(),
                            session_exercise_id=se.id,
                            set_number=s_num,
                            weight_kg=w,
                            reps=reps,
                            reps_in_reserve=rir,
                            is_warmup=(s_num == 1 and random.random() < 0.2),
                            is_dropset=False,
                        )
                        session.add(es)
                        set_count += 1

                current += timedelta(days=1)

            await session.flush()
            print(f"  -> {session_count} sessions, ~{set_count} sets logged")

            # ── weight / body logs ──
            wl_fn = WEIGHT_LOG_FNS[user_idx]
            weight_logs = wl_fn(user.id)
            for wl in weight_logs:
                session.add(wl)
            await session.flush()
            print(f"  -> {len(weight_logs)} weight/body logs")

        await session.commit()
        print(f"\n{'='*60}")
        print("Seed complete!")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(seed())
