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
    
    async def search(self, filters: dict):
        stmt = select(User)

        for field, value in filters.items():
            if hasattr(User, field):
                stmt = stmt.where(getattr(User, field) == value)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update(self, user: User, data: dict):
        for field, value in data.items():
            setattr(user, field, value)

        await self.db.flush()
        return user

    async def soft_delete(self, user: User):
        user.is_active = False
        await self.db.flush()
        return user