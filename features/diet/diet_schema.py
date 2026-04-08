from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class SaveDietPlanSchema(BaseModel):
    content: str = Field(..., min_length=1, description="Full diet plan text")

    model_config = {"populate_by_name": True}


class ResponseDietPlanSchema(BaseModel):
    id: UUID = Field(...)
    content: str = Field(...)
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DietChatRequest(BaseModel):
    question: str = Field(...)
    history: List[dict] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DietChatResponse(BaseModel):
    answer: str = Field(...)

    model_config = {"populate_by_name": True}


class GenerateDietRequest(BaseModel):
    preferences: Optional[str] = Field(None, description="Any specific dietary preferences or restrictions")

    model_config = {"populate_by_name": True}


class GenerateDietResponse(BaseModel):
    diet: str = Field(...)

    model_config = {"populate_by_name": True}
