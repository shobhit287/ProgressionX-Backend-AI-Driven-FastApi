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


class AnalyzeSplitRequest(BaseModel):
    question: str = Field(...)

    model_config = {"populate_by_name": True}


class SessionCoachRequest(BaseModel):
    session_id: UUID = Field(..., alias="sessionId")
    question: str = Field(...)

    model_config = {"populate_by_name": True}


class SessionCoachResponse(BaseModel):
    answer: str = Field(...)

    model_config = {"populate_by_name": True}


class ChatMessageItem(BaseModel):
    role: str = Field(...)
    content: str = Field(...)


class FitnessChatRequest(BaseModel):
    question: str = Field(...)
    history: List[ChatMessageItem] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class FitnessChatResponse(BaseModel):
    answer: str = Field(...)

    model_config = {"populate_by_name": True}


class AIAnalysisResponse(BaseModel):
    analysis: str = Field(...)
    suggestions: List[str] = Field(...)

    model_config = {"populate_by_name": True}


class SessionPlanRequest(BaseModel):
    session_id: UUID = Field(..., alias="sessionId")

    model_config = {"populate_by_name": True}


class PlannedSet(BaseModel):
    set_number: int = Field(..., alias="setNumber")
    weight_kg: float = Field(..., alias="weightKg")
    reps: int = Field(...)
    is_warmup: bool = Field(False, alias="isWarmup")

    model_config = {"populate_by_name": True}


class PlannedExercise(BaseModel):
    exercise_name: str = Field(..., alias="exerciseName")
    sets: List[PlannedSet] = Field(...)

    model_config = {"populate_by_name": True}


class SessionPlanResponse(BaseModel):
    exercises: List[PlannedExercise] = Field(...)
    note: str = Field("")

    model_config = {"populate_by_name": True}


class GeneratedExercise(BaseModel):
    name: str = Field(...)
    display_order: int = Field(..., alias="displayOrder")
    default_sets: int = Field(3, alias="defaultSets")
    exercise_type: str = Field("standard", alias="exerciseType")
    rest_seconds: int = Field(90, alias="restSeconds")
    notes: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class GeneratedDay(BaseModel):
    day: str = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    is_rest: bool = Field(False, alias="isRest")
    exercises: List[GeneratedExercise] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class WeeklyScheduleResponse(BaseModel):
    days: List[GeneratedDay] = Field(...)

    model_config = {"populate_by_name": True}


class GenerateWeeklyScheduleRequest(BaseModel):
    preferences: Optional[str] = Field(None)


class GenerateSplitRequest(BaseModel):
    split_id: UUID = Field(..., alias="splitId")
    preferences: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class GeneratedSplitResponse(BaseModel):
    day: str = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    is_rest: bool = Field(False, alias="isRest")
    exercises: List[GeneratedExercise] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
