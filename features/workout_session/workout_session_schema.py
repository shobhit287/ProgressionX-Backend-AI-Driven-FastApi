from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime, date

from .workout_session_enum import SessionStatusEnum
from features.split_exercise.split_exercise_enum import ExerciseTypeEnum


class StartSessionSchema(BaseModel):
    split_id: UUID = Field(..., alias="splitId")

    model_config = {
        "populate_by_name": True,
    }


class CompleteSessionSchema(BaseModel):
    notes: Optional[str] = Field(None, alias="notes")

    model_config = {
        "populate_by_name": True,
    }


class SessionFilterSchema(BaseModel):
    split_id: Optional[UUID] = Field(None, alias="splitId")
    from_date: Optional[date] = Field(None, alias="fromDate")
    to_date: Optional[date] = Field(None, alias="toDate")
    status: Optional[SessionStatusEnum] = Field(None)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="pageSize")

    model_config = {
        "populate_by_name": True,
    }


class ResponseExerciseSetSchema(BaseModel):
    id: UUID = Field(...)
    set_number: int = Field(..., alias="setNumber")
    weight_kg: float = Field(..., alias="weightKg")
    reps: int = Field(...)
    reps_in_reserve: Optional[int] = Field(None, alias="repsInReserve")
    is_warmup: bool = Field(..., alias="isWarmup")
    is_dropset: bool = Field(..., alias="isDropset")
    description: Optional[str] = Field(None)
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ResponseSessionExerciseSchema(BaseModel):
    id: UUID = Field(...)
    exercise_name: str = Field(..., alias="exerciseName")
    display_order: int = Field(..., alias="displayOrder")
    exercise_type: ExerciseTypeEnum = Field(..., alias="exerciseType")
    superset_group: Optional[int] = Field(None, alias="supersetGroup")
    sets: list[ResponseExerciseSetSchema] = Field(default_factory=list)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ResponseSessionSchema(BaseModel):
    id: UUID = Field(...)
    split_id: UUID = Field(..., alias="splitId")
    started_at: datetime = Field(..., alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    duration_seconds: Optional[int] = Field(None, alias="durationSeconds")
    status: SessionStatusEnum = Field(...)
    notes: Optional[str] = Field(None)
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ResponseSessionDetailSchema(ResponseSessionSchema):
    exercises: list[ResponseSessionExerciseSchema] = Field(default_factory=list)


class PaginatedSessionsSchema(BaseModel):
    items: list[ResponseSessionSchema] = Field(...)
    total: int = Field(...)
    page: int = Field(...)
    page_size: int = Field(..., alias="pageSize")

    model_config = {
        "populate_by_name": True,
    }
