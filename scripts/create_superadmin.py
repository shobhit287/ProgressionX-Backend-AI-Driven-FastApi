"""
Create a superadmin user from .env credentials.

Reads SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD from .env.
If the user already exists, promotes them to superadmin.
If not, creates a new superadmin account with default profile fields.

Usage:
    python scripts/create_superadmin.py
"""

import asyncio

from sqlalchemy import select

from core.config import settings
from core.security import hash_password
from db.database import AsyncSessionLocal
from db.uuid import new_uuid
from features.users.users_model import User
from features.users.users_enum import (
    RoleEnum,
    GoalEnum,
    GenderEnum,
    TrainingTypeEnum,
    ExperienceLevelEnum,
)


async def create_superadmin():
    email = settings.SUPERADMIN_EMAIL.strip().lower()
    password = settings.SUPERADMIN_PASSWORD

    if not email or not password:
        print("Error: SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must be set in .env")
        return

    if len(password) < 8:
        print("Error: SUPERADMIN_PASSWORD must be at least 8 characters")
        return

    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role == RoleEnum.SUPERADMIN:
                print(f"Superadmin already exists: {existing.first_name} {existing.last_name} ({email})")
                return

            existing.role = RoleEnum.SUPERADMIN
            await db.commit()
            print(f"Promoted existing user to superadmin: {existing.first_name} {existing.last_name} ({email})")
            return

        # Create new superadmin with default profile fields
        user = User(
            id=new_uuid(),
            first_name="Super",
            last_name="Admin",
            age=30,
            weight=75.0,
            height=175,
            goal=GoalEnum.MAINTENANCE,
            gender=GenderEnum.MALE,
            training_type=TrainingTypeEnum.GENERAL_FITNESS,
            experience_level=ExperienceLevelEnum.ADVANCED,
            activity_level="Admin account",
            email=email,
            hashed_password=hash_password(password),
            role=RoleEnum.SUPERADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"Superadmin created successfully: {email}")


if __name__ == "__main__":
    asyncio.run(create_superadmin())
