from core.security import hash_password, verify_password
from core.exception_handlers import BaseDomainError
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .user_repository import UserRepository


class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repository = UserRepository(db)

    async def create(self, payload: dict):
        password = payload.pop("password")
        payload["hashed_password"] = hash_password(password)

        #normalize email
        payload["email"] = payload["email"].strip().lower()

        user = await self.user_repository.create(payload)
        return user
    
    async def get_by_id(self, id: UUID):
        return await self.user_repository.get_by_id(id)
    
    async def get_by_email(self, email: str):
        users = await self.user_repository.search({"email": email})
        return users[0] if users else None
    
                    
    async def update(self, id: UUID, payload: dict):
        user = await self.user_repository.get_by_id(id)
        updated_user = await self.user_repository.update(user, payload)
        return updated_user
    
    async def change_password(self, id: UUID, old_password: str, new_password: str):
        user = await self.user_repository.get_by_id(id)
        if not verify_password(old_password, user.hashed_password):
            raise BaseDomainError("Current password is incorrect", 400)
        user.hashed_password = hash_password(new_password)
        await self.user_repository.update(user, {})
        return user

    async def delete(self, id: UUID):
        user = await self.user_repository.get_by_id(id)
        await self.user_repository.soft_delete(user)
    

