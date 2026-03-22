from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class CreateExerciseSetSchema(BaseModel):
    weight_kg: float = Field(..., alias="weightKg")
    reps: int = Field(..., alias="reps")
    reps_in_reserve: Optional[int] = Field(None, alias="repsInReserve", ge=0, le=5)
    is_warmup: bool = Field(False, alias="isWarmup")
    is_dropset: bool = Field(False, alias="isDropset")
    description: Optional[str] = Field(None)

    model_config = {
        "populate_by_name": True,
    }


class UpdateExerciseSetSchema(BaseModel):
    weight_kg: Optional[float] = Field(None, alias="weightKg")
    reps: Optional[int] = Field(None, alias="reps")
    reps_in_reserve: Optional[int] = Field(None, alias="repsInReserve", ge=0, le=5)
    is_warmup: Optional[bool] = Field(None, alias="isWarmup")
    is_dropset: Optional[bool] = Field(None, alias="isDropset")
    description: Optional[str] = Field(None)

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
