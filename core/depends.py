from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from db.database import AsyncSessionLocal
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends

from .security import verify_token, token_bearer
from .exception_handlers import BaseDomainError
from features.users.users_service import UserService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(token_bearer),
    db: AsyncSession = Depends(get_db),
):
    user_service = UserService(db)

    # validate token
    token = credentials.credentials
    payload = verify_token(token)

    user_id: str = payload.get("id")
    user = await user_service.get_by_id(user_id)
    return user


async def require_superadmin(user=Depends(current_user)):
    """Dependency that ensures the authenticated user is a superadmin."""
    if user.role != "superadmin":
        raise BaseDomainError("Forbidden", 403)
    return user


async def require_complete_profile(user=Depends(current_user)):
    """Gate for endpoints that depend on the user's full fitness profile
    (AI prompts, analytics, export reports). Stub Google signups whose
    profile hasn't been filled yet are blocked server-side so they can't
    bypass the frontend's AuthGuard via direct API calls."""
    if not user.is_profile_complete:
        raise BaseDomainError(
            "Please complete your profile before using this feature.", 403
        )
    return user

