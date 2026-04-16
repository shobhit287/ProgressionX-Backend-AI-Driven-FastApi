from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# --- Dashboard stats ---

class AdminDashboardResponse(BaseModel):
    total_users: int = Field(..., alias="totalUsers")
    active_users_7d: int = Field(..., alias="activeUsers7d")
    active_users_30d: int = Field(..., alias="activeUsers30d")
    new_users_today: int = Field(..., alias="newUsersToday")
    new_users_this_week: int = Field(..., alias="newUsersThisWeek")
    new_users_this_month: int = Field(..., alias="newUsersThisMonth")
    total_sessions: int = Field(..., alias="totalSessions")
    sessions_today: int = Field(..., alias="sessionsToday")
    avg_session_duration: Optional[float] = Field(None, alias="avgSessionDuration")
    total_llm_calls_today: int = Field(..., alias="totalLlmCallsToday")
    total_llm_calls_month: int = Field(..., alias="totalLlmCallsMonth")
    total_tokens_month: int = Field(..., alias="totalTokensMonth")

    model_config = {"populate_by_name": True}


# --- Active hours heatmap ---

class ActiveHourBucket(BaseModel):
    hour: int
    day_of_week: int = Field(..., alias="dayOfWeek")
    count: int

    model_config = {"populate_by_name": True}


class ActiveHoursResponse(BaseModel):
    buckets: list[ActiveHourBucket]
    peak_hour: int = Field(..., alias="peakHour")
    peak_day: int = Field(..., alias="peakDay")

    model_config = {"populate_by_name": True}


# --- LLM usage ---

class LlmEndpointBreakdown(BaseModel):
    endpoint: str
    count: int
    avg_duration_ms: Optional[float] = Field(None, alias="avgDurationMs")
    total_input_tokens: int = Field(0, alias="totalInputTokens")
    total_output_tokens: int = Field(0, alias="totalOutputTokens")

    model_config = {"populate_by_name": True}


class LlmDailyCount(BaseModel):
    date: str
    count: int
    tokens: int


class LlmUsageResponse(BaseModel):
    total_calls: int = Field(..., alias="totalCalls")
    total_errors: int = Field(..., alias="totalErrors")
    error_rate: float = Field(..., alias="errorRate")
    total_input_tokens: int = Field(..., alias="totalInputTokens")
    total_output_tokens: int = Field(..., alias="totalOutputTokens")
    avg_duration_ms: Optional[float] = Field(None, alias="avgDurationMs")
    by_endpoint: list[LlmEndpointBreakdown] = Field(..., alias="byEndpoint")
    daily: list[LlmDailyCount]
    top_users: list["LlmTopUser"] = Field(..., alias="topUsers")

    model_config = {"populate_by_name": True}


class LlmTopUser(BaseModel):
    user_id: UUID = Field(..., alias="userId")
    email: str
    name: str
    call_count: int = Field(..., alias="callCount")

    model_config = {"populate_by_name": True}


# --- User list ---

class AdminUserItem(BaseModel):
    id: UUID
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    email: str
    goal: str
    training_type: str = Field(..., alias="trainingType")
    experience_level: str = Field(..., alias="experienceLevel")
    role: str
    is_active: bool = Field(..., alias="isActive")
    created_at: datetime = Field(..., alias="createdAt")
    last_active: Optional[datetime] = Field(None, alias="lastActive")
    total_sessions: int = Field(0, alias="totalSessions")
    total_llm_calls: int = Field(0, alias="totalLlmCalls")

    model_config = {"populate_by_name": True}


class AdminUsersResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")

    model_config = {"populate_by_name": True}
