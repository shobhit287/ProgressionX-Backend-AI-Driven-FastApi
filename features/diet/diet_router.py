from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db, current_user
from core.rate_limiter import limiter
from core.groq_client import set_llm_context
from .diet_schema import (
    SaveDietPlanSchema,
    ResponseDietPlanSchema,
    DietChatRequest,
    DietChatResponse,
    GenerateDietRequest,
    GenerateDietResponse,
)
from .diet_service import DietService


router = APIRouter(prefix="/diet", tags=["Diet"])


@router.get(
    "/plan",
    status_code=status.HTTP_200_OK,
    response_model=ResponseDietPlanSchema | None,
)
async def get_diet_plan(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    return await service.get_plan(user.id)


@router.put(
    "/plan",
    status_code=status.HTTP_200_OK,
    response_model=ResponseDietPlanSchema,
)
async def save_diet_plan(
    data: SaveDietPlanSchema,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    plan = await service.save_plan(user.id, data.content)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete(
    "/plan",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_diet_plan(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DietService(db)
    await service.delete_plan(user.id)
    await db.commit()
    return None


@router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    response_model=DietChatResponse,
)
@limiter.limit("5/minute")
async def diet_chat(
    request: Request,
    data: DietChatRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    set_llm_context(user_id=str(user.id), endpoint="diet-chat")
    service = DietService(db)
    result = await service.chat(user.id, data.question, data.history)
    return result


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    response_model=GenerateDietResponse,
)
@limiter.limit("2/minute")
async def generate_diet(
    request: Request,
    data: GenerateDietRequest = None,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    set_llm_context(user_id=str(user.id), endpoint="diet-generate")
    service = DietService(db)
    preferences = data.preferences if data else None
    result = await service.generate_diet(user.id, preferences)
    return result
