from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from .users_enum import GoalEnum, GenderEnum


# Create User Schema
class CreateUserSchema(BaseModel):
    first_name: str = Field(..., alias="firstName", description="First name of the user")
    last_name: str = Field(..., alias="lastName", description="Last name of the user")

    age: int = Field(..., description="Age of the user in years")
    weight: float = Field(..., description="Weight of the user in kilograms")
    height: int = Field(..., description="Height of the user in centimeters")

    goal: GoalEnum = Field(..., description="Fitness goal of the user")
    gender: GenderEnum = Field(..., description="Gender of the user")

    mobile_number: Optional[str] = Field(None, alias="mobileNumber", description="Mobile number of the user")
    email: EmailStr = Field(..., description="Email address of the user")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "firstName": "John",
                "lastName": "Doe",
                "age": 28,
                "weight": 75.5,
                "height": 178,
                "goal": "bulking",
                "gender": "male",
                "mobileNumber": "9876543210",
                "email": "john.doe@example.com",
                "password": "strongpassword123"
            }
        }
    }


# Update User Schema
class UpdateUserSchema(BaseModel):
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")

    age: Optional[int] = Field(None)
    weight: Optional[float] = Field(None)
    height: Optional[int] = Field(None)

    goal: Optional[GoalEnum] = Field(None)
    gender: Optional[GenderEnum] = Field(None)

    mobile_number: Optional[str] = Field(None, alias="mobileNumber")
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "firstName": "John",
                "weight": 78.0,
                "goal": "cutting",
                "isActive": True
            }
        }
    }


# Response User Schema
class ResponseUserSchema(BaseModel):
    id: UUID = Field(...)
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")

    age: int = Field(...)
    weight: float = Field(...)
    height: int = Field(...)

    goal: GoalEnum = Field(...)
    gender: GenderEnum = Field(...)

    mobile_number: Optional[str] = Field(None, alias="mobileNumber")
    email: EmailStr = Field(...)
    is_active: bool = Field(..., alias="isActive")

    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "firstName": "John",
                "lastName": "Doe",
                "age": 28,
                "weight": 75.5,
                "height": 178,
                "goal": "maintenance",
                "gender": "male",
                "mobileNumber": "9876543210",
                "email": "john.doe@example.com",
                "isActive": True,
                "createdAt": "2026-03-01T10:00:00Z",
                "updatedAt": "2026-03-01T12:30:00Z"
            }
        }
    }