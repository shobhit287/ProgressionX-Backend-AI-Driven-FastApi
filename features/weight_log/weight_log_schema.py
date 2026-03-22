from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime


class CreateWeightLogSchema(BaseModel):
    weight_kg: float = Field(..., alias="weightKg")
    waist_cm: Optional[float] = Field(None, alias="waistCm")
    body_fat_pct: Optional[float] = Field(None, alias="bodyFatPct")
    description: Optional[str] = Field(None)
    logged_at: Optional[date] = Field(None, alias="loggedAt")

    model_config = {"populate_by_name": True}


class UpdateWeightLogSchema(BaseModel):
    weight_kg: Optional[float] = Field(None, alias="weightKg")
    waist_cm: Optional[float] = Field(None, alias="waistCm")
    body_fat_pct: Optional[float] = Field(None, alias="bodyFatPct")
    description: Optional[str] = Field(None)
    logged_at: Optional[date] = Field(None, alias="loggedAt")

    model_config = {"populate_by_name": True}


class WeightLogFilterSchema(BaseModel):
    from_date: Optional[date] = Field(None, alias="fromDate")
    to_date: Optional[date] = Field(None, alias="toDate")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}


class ResponseWeightLogSchema(BaseModel):
    id: UUID = Field(...)
    user_id: UUID = Field(..., alias="userId")
    weight_kg: float = Field(..., alias="weightKg")
    waist_cm: Optional[float] = Field(None, alias="waistCm")
    body_fat_pct: Optional[float] = Field(None, alias="bodyFatPct")
    description: Optional[str] = Field(None)
    logged_at: date = Field(..., alias="loggedAt")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}


class WeeklyAverageSchema(BaseModel):
    week_start: date = Field(..., alias="weekStart")
    average_weight: float = Field(..., alias="averageWeight")
    entries: int = Field(...)

    model_config = {"populate_by_name": True}


class WeightAnalyticsSchema(BaseModel):
    weekly_averages: List[WeeklyAverageSchema] = Field(..., alias="weeklyAverages")
    rate_of_change: float = Field(..., alias="rateOfChange")
    total_change: float = Field(..., alias="totalChange")
    entries: int = Field(...)

    model_config = {"populate_by_name": True}
