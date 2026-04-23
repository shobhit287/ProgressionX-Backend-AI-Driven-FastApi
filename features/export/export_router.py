from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.depends import get_db, require_complete_profile
from core.rate_limiter import limiter

from .export_schema import ExportFiltersResponse, ExportPdfRequest, ExportPdfResponse
from .export_service import ExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.get(
    "/filters",
    status_code=status.HTTP_200_OK,
    response_model=ExportFiltersResponse,
)
async def get_export_filters(
    user=Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    service = ExportService(db)
    return await service.get_filters(user.id)


@router.post(
    "/pdf",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ExportPdfResponse,
)
@limiter.limit("5/minute")
async def export_pdf(
    request: Request,
    data: ExportPdfRequest,
    background_tasks: BackgroundTasks,
    user=Depends(require_complete_profile),
):
    background_tasks.add_task(
        ExportService.run_export_job,
        user.id,
        data.start_date,
        data.end_date,
        data.split_id,
        data.exercise_name,
    )
    return ExportPdfResponse(
        message=(
            "Your report is being generated. You'll receive it by email at "
            f"{user.email} in a few moments."
        ),
        email=user.email,
    )
