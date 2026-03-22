from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

from .workout_split_enum import DayEnum


class CreateWorkoutSplitSchema(BaseModel):
    name: str = Field(..., description="Name of the workout split")
    day: DayEnum = Field(..., description="Day of the week")
    description: Optional[str] = Field(None, description="Description of the workout split")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "Push Day",
                "day": "monday",
                "description": "Chest, shoulders, triceps"
            }
        }
    }


class UpdateWorkoutSplitSchema(BaseModel):
    name: Optional[str] = Field(None, description="Name of the workout split")
    day: Optional[DayEnum] = Field(None, description="Day of the week")
    description: Optional[str] = Field(None, description="Description of the workout split")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "Pull Day",
                "day": "tuesday"
            }
        }
    }


class ResponseWorkoutSplitSchema(BaseModel):
    id: UUID = Field(...)
    name: str = Field(...)
    day: DayEnum = Field(...)
    user_id: UUID = Field(..., alias="userId")
    description: Optional[str] = Field(None)

    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Push Day",
                "day": "monday",
                "userId": "660e8400-e29b-41d4-a716-446655440000",
                "description": "Chest, shoulders, triceps",
                "createdAt": "2026-03-01T10:00:00Z",
                "updatedAt": "2026-03-01T12:30:00Z"
            }
        }
    }
