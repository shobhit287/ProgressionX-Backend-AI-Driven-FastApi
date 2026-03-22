from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

from .split_exercise_enum import ExerciseTypeEnum


class CreateSplitExerciseSchema(BaseModel):
    name: str = Field(..., description="Name of the exercise")
    display_order: Optional[int] = Field(None, alias="displayOrder", description="Display order")
    default_sets: int = Field(3, alias="defaultSets", description="Default number of sets")
    exercise_type: ExerciseTypeEnum = Field(
        ExerciseTypeEnum.STANDARD, alias="exerciseType", description="Type of exercise"
    )
    superset_group: Optional[int] = Field(None, alias="supersetGroup", description="Superset group number")
    notes: Optional[str] = Field(None, description="Additional notes")
    rest_seconds: int = Field(90, alias="restSeconds", description="Rest time in seconds")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "Bench Press",
                "displayOrder": 1,
                "defaultSets": 4,
                "exerciseType": "standard",
                "restSeconds": 120,
                "notes": "Focus on form"
            }
        }
    }


class UpdateSplitExerciseSchema(BaseModel):
    name: Optional[str] = Field(None, description="Name of the exercise")
    display_order: Optional[int] = Field(None, alias="displayOrder")
    default_sets: Optional[int] = Field(None, alias="defaultSets")
    exercise_type: Optional[ExerciseTypeEnum] = Field(None, alias="exerciseType")
    superset_group: Optional[int] = Field(None, alias="supersetGroup")
    notes: Optional[str] = Field(None)
    rest_seconds: Optional[int] = Field(None, alias="restSeconds")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "Incline Bench Press",
                "defaultSets": 3
            }
        }
    }


class ReorderItemSchema(BaseModel):
    id: UUID = Field(..., description="Exercise ID")
    display_order: int = Field(..., alias="displayOrder", description="New display order")

    model_config = {
        "populate_by_name": True,
    }


class ReorderSchema(BaseModel):
    exercises: list[ReorderItemSchema] = Field(..., description="List of exercises with new order")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "exercises": [
                    {"id": "550e8400-e29b-41d4-a716-446655440000", "displayOrder": 1},
                    {"id": "660e8400-e29b-41d4-a716-446655440000", "displayOrder": 2}
                ]
            }
        }
    }


class ResponseSplitExerciseSchema(BaseModel):
    id: UUID = Field(...)
    split_id: UUID = Field(..., alias="splitId")
    name: str = Field(...)
    display_order: int = Field(..., alias="displayOrder")
    default_sets: int = Field(..., alias="defaultSets")
    exercise_type: ExerciseTypeEnum = Field(..., alias="exerciseType")
    superset_group: Optional[int] = Field(None, alias="supersetGroup")
    notes: Optional[str] = Field(None)
    rest_seconds: int = Field(..., alias="restSeconds")

    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "splitId": "660e8400-e29b-41d4-a716-446655440000",
                "name": "Bench Press",
                "displayOrder": 1,
                "defaultSets": 4,
                "exerciseType": "standard",
                "supersetGroup": None,
                "notes": "Focus on form",
                "restSeconds": 120,
                "createdAt": "2026-03-01T10:00:00Z",
                "updatedAt": "2026-03-01T12:30:00Z"
            }
        }
    }
