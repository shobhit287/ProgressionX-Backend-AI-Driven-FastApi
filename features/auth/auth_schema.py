from pydantic import BaseModel, EmailStr, Field


class LoginDto(BaseModel):
    email: EmailStr = Field(..., description="Email of user")
    password: str = Field(..., description="Password of user", min_length=6)

class TokenDto(BaseModel):
    access_token: str = Field(..., alias="accessToken", description="Access token")
    refresh_token: str = Field(..., alias="refreshToken", description="Refresh token")

    class Config:
        validate_by_name = True

