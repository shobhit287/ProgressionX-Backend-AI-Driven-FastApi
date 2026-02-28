from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from .users_enum import GoalEnum, GenderEnum


# Create User Schema
class CreateUserSchema(BaseModel):
    first_name: str = Field(
        ...,
        alias="firstName",
        description="First name of the user"
    )
    last_name: str = Field(
        ...,
        alias="lastName",
        description="Last name of the user"
    )

    age: int = Field(
        ...,
        description="Age of the user in years"
    )
    weight: float = Field(
        ...,
        description="Weight of the user in kilograms"
    )
    height: int = Field(
        ...,
        description="Height of the user in centimeters"
    )

    goal: GoalEnum = Field(
        ...,
        description="Fitness goal of the user (e.g., muscle_gain, fat_loss)"
    )
    gender: GenderEnum = Field(
        ...,
        description="Gender of the user"
    )

    mobile_number: Optional[str] = Field(
        None,
        alias="mobileNumber",
        description="Mobile number of the user including country code"
    )

    email: EmailStr = Field(
        ...,
        description="Email address of the user"
    )

    password: str = Field(
        ...,
        min_length=8,
        description="User password (minimum 8 characters)"
    )

    model_config = {
        "populate_by_name": True
    }


# Update User Schema
class UpdateUserSchema(BaseModel):
    first_name: Optional[str] = Field(
        None,
        alias="firstName",
        description="Updated first name of the user"
    )
    last_name: Optional[str] = Field(
        None,
        alias="lastName",
        description="Updated last name of the user"
    )

    age: Optional[int] = Field(
        None,
        description="Updated age of the user"
    )
    weight: Optional[float] = Field(
        None,
        description="Updated weight in kilograms"
    )
    height: Optional[int] = Field(
        None,
        description="Updated height in centimeters"
    )

    goal: Optional[GoalEnum] = Field(
        None,
        description="Updated fitness goal"
    )
    gender: Optional[GenderEnum] = Field(
        None,
        description="Updated gender"
    )

    mobile_number: Optional[str] = Field(
        None,
        alias="mobileNumber",
        description="Updated mobile number"
    )

    is_active: Optional[str] = Field(
        None,
        alias="isActive",
        description="User active status (true or false)"
    )

    model_config = {
        "populate_by_name": True
    }


# Response User Schema
class ResponseUserSchema(BaseModel):
    id: UUID = Field(
        ...,
        description="Unique identifier of the user"
    )

    first_name: str = Field(
        ...,
        alias="firstName",
        description="First name of the user"
    )
    last_name: str = Field(
        ...,
        alias="lastName",
        description="Last name of the user"
    )

    age: int = Field(
        ...,
        description="Age of the user"
    )
    weight: float = Field(
        ...,
        description="Weight of the user in kilograms"
    )
    height: int = Field(
        ...,
        description="Height of the user in centimeters"
    )

    goal: GoalEnum = Field(
        ...,
        description="Fitness goal of the user"
    )
    gender: GenderEnum = Field(
        ...,
        description="Gender of the user"
    )

    mobile_number: Optional[str] = Field(
        None,
        alias="mobileNumber",
        description="Mobile number of the user"
    )

    email: EmailStr = Field(
        ...,
        description="Email address of the user"
    )

    is_active: bool = Field(
        ...,
        alias="isActive",
        description="User active status (true or false)"
    )

    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="Timestamp when the user was created"
    )
    updated_at: datetime = Field(
        ...,
        alias="updatedAt",
        description="Timestamp when the user was last updated"
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }