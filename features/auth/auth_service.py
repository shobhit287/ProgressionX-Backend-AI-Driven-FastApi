from sqlalchemy.ext.asyncio import AsyncSession

from features.users.users_service import UserService
from core.security import verify_password, create_access_token
from core.exception_handlers import BaseDomainError


class AuthService:
    def __init__(self, db: AsyncSession):
      self.db = db
      self.users_service = UserService(db)

    async def login(self, payload: dict) -> dict:
      email = payload.get("email", "").strip().lower()
      user = await self.users_service.get_by_email(email)
      if not user or not verify_password(payload.get("password"), user.hashed_password):
          raise BaseDomainError("Invalid Credentials", 401)
          
      access_token = create_access_token({"id": str(user.id)})
      refresh_token = create_access_token({"id": str(user.id)}, 2880)
      return {
               "access_token": access_token,
               "refresh_token": refresh_token
            }