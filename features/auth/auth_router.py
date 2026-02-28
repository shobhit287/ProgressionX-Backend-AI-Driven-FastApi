from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.orm import Session

from core.depends import get_db
from api.auth.auth_dto import LoginDto, TokenDto
from api.auth import auth_service

router = APIRouter(prefix="/auth",  tags=["Auth"])

@router.post("/login", response_model = TokenDto)
def login(data: LoginDto, db: Session = Depends(get_db)) -> TokenDto:
    return auth_service.login(data, db)

