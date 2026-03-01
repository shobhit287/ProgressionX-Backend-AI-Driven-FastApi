from pydantic import BaseModel, EmailStr, Field


class LoginSchema(BaseModel):
    email: EmailStr = Field(..., description="Email of user")
    password: str = Field(..., description="Password of user", min_length=8)

class TokenSchema(BaseModel):
    access_token: str = Field(..., alias="accessToken", description="Access token")
    refresh_token: str = Field(..., alias="refreshToken", description="Refresh token")
    token_type: str = Field(default="bearer", alias="tokenType")

    class Config:
        validate_by_name = True

