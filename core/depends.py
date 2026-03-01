from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from db.database import AsyncSessionLocal
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends


from .security import verify_token, token_bearer
from features.users.users_service import UserService

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(token_bearer), db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    
    #validate token
    token = credentials.credentials
    payload = verify_token(token)
   
    user_id: str = payload.get("id")
    user = await user_service.get_by_id(user_id)
    return user

