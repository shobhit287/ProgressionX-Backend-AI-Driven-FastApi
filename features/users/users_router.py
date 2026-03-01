from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db, current_user
from .users_schema import CreateUserSchema, UpdateUserSchema, ResponseUserSchema
from .users_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseUserSchema
)
async def create_user(
    data: CreateUserSchema,
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.create(data.model_dump())
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", status_code=status.HTTP_200_OK, response_model=ResponseUserSchema)
async def get_by_id(
    user = Depends(current_user),
) -> ResponseUserSchema:
    return user

@router.patch("", status_code=status.HTTP_200_OK, response_model=ResponseUserSchema)
async def update(
    data: UpdateUserSchema,
    user = Depends(current_user),
    db: AsyncSession = Depends(get_db)
) -> ResponseUserSchema:
    user_service = UserService(db)
    user = await user_service.update(user.id, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    user = Depends(current_user),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    await user_service.delete(user.id)
    await db.commit()
    return None    
