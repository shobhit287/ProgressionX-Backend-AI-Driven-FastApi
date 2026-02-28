from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.exception_handlers import BaseDomainError
from .users_model import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_data: dict) -> User:
        try:
            user = User(**user_data)
            self.db.add(user)
            await self.db.flush()
            return user

        except IntegrityError:
            raise BaseDomainError("User already exists", 409)

    async def get_by_id(self, id):
        result = await self.db.execute(
            select(User).where(User.id == id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise BaseDomainError("User not found", 404)

        return user

    async def update(self, user: User, data: dict):
        for field, value in data.items():
            setattr(user, field, value)

        await self.db.flush()
        return user