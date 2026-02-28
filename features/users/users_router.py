from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from core.depends import get_db
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

        async with db.begin():
            user = await user_service.create(data.model_dump())

        await db.refresh(user)
        return user


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=ResponseUserSchema)
async def get_by_id(
    id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
) -> ResponseUserSchema:
    user_service = UserService(db)
    return await user_service.get_by_id(
        id
    )

@router.patch("/{id}", status_code=status.HTTP_200_OK, response_model=ResponseUserSchema)
async def update(
    data: UpdateUserSchema,
    id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
) -> ResponseUserSchema:
    user_service = UserService(db)
    async with db.begin():
        user = await user_service.update(id, data.model_dump(exclude_unset=True))

    await db.refresh(user)
    return user


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    async with db.begin():
        await user_service.delete(id)
