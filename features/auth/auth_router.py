from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db
from core.rate_limiter import limiter
from .auth_schema import LoginSchema, TokenSchema, RefreshSchema
from .auth_service import AuthService

router = APIRouter(prefix="/auth",  tags=["Auth"])

@router.post("/login", status_code=status.HTTP_200_OK, response_model = TokenSchema)
@limiter.limit("5/minute")
async def login(request: Request, data: LoginSchema,  db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.login(data.model_dump())

@router.post("/refresh", status_code=status.HTTP_200_OK, response_model = TokenSchema)
async def refresh(data: RefreshSchema, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.refresh(data.refresh_token)
