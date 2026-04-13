from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db, current_user
from core.rate_limiter import limiter
from .ai_schema import (
    AnalyzeSessionsRequest,
    AnalyzeExerciseRequest,
    AnalyzeWeightRequest,
    AIAnalysisResponse,
    SessionCoachRequest,
    SessionCoachResponse,
    FitnessChatRequest,
    FitnessChatResponse,
    SessionPlanRequest,
    SessionPlanResponse,
    WeeklyScheduleResponse,
    GenerateWeeklyScheduleRequest,
    GenerateSplitRequest,
    GeneratedSplitResponse,
)
from .ai_service import AIService


router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@router.post(
    "/analyze-sessions",
    status_code=status.HTTP_200_OK,
    response_model=AIAnalysisResponse,
)
@limiter.limit("3/minute")
async def analyze_sessions(
    request: Request,
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
@limiter.limit("3/minute")
async def analyze_exercise(
    request: Request,
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
@limiter.limit("3/minute")
async def analyze_weight(
    request: Request,
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
    "/chat",
    status_code=status.HTTP_200_OK,
    response_model=FitnessChatResponse,
)
@limiter.limit("5/minute")
async def fitness_chat(
    request: Request,
    data: FitnessChatRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    result = await service.fitness_chat(
        user.id,
        question=data.question,
        history=[msg.model_dump() for msg in data.history],
    )
    return result


@router.post(
    "/session-coach",
    status_code=status.HTTP_200_OK,
    response_model=SessionCoachResponse,
)
@limiter.limit("5/minute")
async def session_coach(
    request: Request,
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


@router.post(
    "/generate-weekly-schedule",
    status_code=status.HTTP_200_OK,
    response_model=WeeklyScheduleResponse,
)
@limiter.limit("3/hour")
async def generate_weekly_schedule(
    request: Request,
    data: GenerateWeeklyScheduleRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    return await service.generate_weekly_schedule(user.id, preferences=data.preferences)


@router.post(
    "/customize-split",
    status_code=status.HTTP_200_OK,
    response_model=GeneratedSplitResponse,
)
@limiter.limit("10/hour")
async def customize_split(
    request: Request,
    data: GenerateSplitRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    return await service.generate_custom_split(
        user.id, split_id=data.split_id, preferences=data.preferences
    )


@router.post(
    "/session-plan",
    status_code=status.HTTP_200_OK,
    response_model=SessionPlanResponse,
)
@limiter.limit("2/minute")
async def session_plan(
    request: Request,
    data: SessionPlanRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AIService(db)
    result = await service.generate_session_plan(
        user.id,
        session_id=data.session_id,
    )
    return result
