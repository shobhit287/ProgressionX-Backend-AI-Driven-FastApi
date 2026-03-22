from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date


class AnalyzeSessionsRequest(BaseModel):
    split_id: Optional[UUID] = Field(None, alias="splitId")
    from_date: Optional[date] = Field(None, alias="fromDate")
    to_date: Optional[date] = Field(None, alias="toDate")
    question: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class AnalyzeExerciseRequest(BaseModel):
    exercise_name: str = Field(..., alias="exerciseName")
    from_date: Optional[date] = Field(None, alias="fromDate")
    to_date: Optional[date] = Field(None, alias="toDate")
    question: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class AnalyzeWeightRequest(BaseModel):
    from_date: Optional[date] = Field(None, alias="fromDate")
    to_date: Optional[date] = Field(None, alias="toDate")
    question: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class AIAnalysisResponse(BaseModel):
    analysis: str = Field(...)
    suggestions: List[str] = Field(...)

    model_config = {"populate_by_name": True}
