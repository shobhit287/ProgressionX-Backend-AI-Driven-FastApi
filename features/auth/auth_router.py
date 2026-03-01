from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db
from .auth_schema import LoginSchema, TokenSchema
from .auth_service import AuthService

router = APIRouter(prefix="/auth",  tags=["Auth"])

@router.post("/login", status_code=status.HTTP_200_OK, response_model = TokenSchema)
async def login(data: LoginSchema,  db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.login(data.model_dump())

