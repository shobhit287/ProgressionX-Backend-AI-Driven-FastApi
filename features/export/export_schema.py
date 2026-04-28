from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ExportFiltersResponse(BaseModel):
    splits: list[dict] = Field(default_factory=list)
    exercises: list[str] = Field(default_factory=list)


class ExportPdfResponse(BaseModel):
    message: str
    email: str


class ExportPdfRequest(BaseModel):
    start_date: date = Field(..., alias="startDate")
    end_date: date = Field(..., alias="endDate")
    split_id: Optional[UUID] = Field(None, alias="splitId")
    exercise_name: Optional[str] = Field(None, alias="exerciseName")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("endDate must be on or after startDate")
        return self


class ExportWorkoutHistoryRequest(BaseModel):
    """Workout-history-only export. All three fields are required —
    user must pick a specific split (no all-splits option) and an
    explicit start/end window."""

    split_id: UUID = Field(..., alias="splitId")
    start_date: date = Field(..., alias="startDate")
    end_date: date = Field(..., alias="endDate")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("endDate must be on or after startDate")
        return self
