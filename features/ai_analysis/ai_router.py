from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db, current_user
from .ai_schema import (
    AnalyzeSessionsRequest,
    AnalyzeExerciseRequest,
    AnalyzeWeightRequest,
    AIAnalysisResponse,
    SessionCoachRequest,
    SessionCoachResponse,
)
from .ai_service import AIService


router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@router.post(
    "/analyze-sessions",
    status_code=status.HTTP_200_OK,
    response_model=AIAnalysisResponse,
)
async def analyze_sessions(
    data: AnalyzeSessionsRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    result = await service.analyze_sessions(
        user.id,
        split_id=data.split_id,
        from_date=data.from_date,
        to_date=data.to_date,
        question=data.question,
    )
    return result


@router.post(
    "/analyze-exercise",
    status_code=status.HTTP_200_OK,
    response_model=AIAnalysisResponse,
)
async def analyze_exercise(
    data: AnalyzeExerciseRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    result = await service.analyze_exercise(
        user.id,
        exercise_name=data.exercise_name,
        from_date=data.from_date,
        to_date=data.to_date,
        question=data.question,
    )
    return result


@router.post(
    "/analyze-weight",
    status_code=status.HTTP_200_OK,
    response_model=AIAnalysisResponse,
)
async def analyze_weight(
    data: AnalyzeWeightRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    result = await service.analyze_weight(
        user.id,
        from_date=data.from_date,
        to_date=data.to_date,
        question=data.question,
    )
    return result


@router.post(
    "/session-coach",
    status_code=status.HTTP_200_OK,
    response_model=SessionCoachResponse,
)
async def session_coach(
    data: SessionCoachRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    result = await service.session_coach(
        user.id,
        session_id=data.session_id,
        question=data.question,
    )
    return result
