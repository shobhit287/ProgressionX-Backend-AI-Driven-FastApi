from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
import datetime


class SessionAnalyticsQuery(BaseModel):
    split_id: Optional[UUID] = Field(None, alias="splitId")
    from_date: Optional[datetime.date] = Field(None, alias="fromDate")
    to_date: Optional[datetime.date] = Field(None, alias="toDate")

    model_config = {"populate_by_name": True}


class ExerciseAnalyticsQuery(BaseModel):
    from_date: Optional[datetime.date] = Field(None, alias="fromDate")
    to_date: Optional[datetime.date] = Field(None, alias="toDate")

    model_config = {"populate_by_name": True}


class SessionDataPoint(BaseModel):
    session_date: datetime.date = Field(..., alias="date")
    total_volume: float = Field(..., alias="totalVolume")
    total_sets: int = Field(..., alias="totalSets")
    total_reps: int = Field(..., alias="totalReps")
    avg_rir: Optional[float] = Field(None, alias="avgRir")
    duration_seconds: Optional[int] = Field(None, alias="durationSeconds")
    exercise_count: int = Field(..., alias="exerciseCount")

    model_config = {"populate_by_name": True}


class SessionAnalyticsResponse(BaseModel):
    sessions: List[SessionDataPoint] = Field(...)

    model_config = {"populate_by_name": True}


class PersonalRecord(BaseModel):
    weight: float = Field(...)
    reps: int = Field(...)
    estimated_1rm: float = Field(..., alias="estimated1Rm")
    record_date: datetime.date = Field(..., alias="date")

    model_config = {"populate_by_name": True}


class ExerciseDataPoint(BaseModel):
    session_date: datetime.date = Field(..., alias="date")
    session_id: UUID = Field(..., alias="sessionId")
    max_weight: float = Field(..., alias="maxWeight")
    total_volume: float = Field(..., alias="totalVolume")
    total_reps: int = Field(..., alias="totalReps")
    total_sets: int = Field(..., alias="totalSets")
    estimated_1rm: float = Field(..., alias="estimated1Rm")
    avg_rir: Optional[float] = Field(None, alias="avgRir")

    model_config = {"populate_by_name": True}


class ExerciseAnalyticsResponse(BaseModel):
    data_points: List[ExerciseDataPoint] = Field(..., alias="dataPoints")
    personal_record: Optional[PersonalRecord] = Field(None, alias="personalRecord")

    model_config = {"populate_by_name": True}


class PREntry(BaseModel):
    exercise_name: str = Field(..., alias="exerciseName")
    weight: float = Field(...)
    reps: int = Field(...)
    estimated_1rm: float = Field(..., alias="estimated1Rm")
    record_date: datetime.date = Field(..., alias="date")

    model_config = {"populate_by_name": True}


class DashboardSummaryResponse(BaseModel):
    week_sessions: int = Field(..., alias="weekSessions")
    current_streak: int = Field(..., alias="currentStreak")
    total_sessions: int = Field(..., alias="totalSessions")
    personal_records: List[PREntry] = Field(..., alias="personalRecords")

    model_config = {"populate_by_name": True}
