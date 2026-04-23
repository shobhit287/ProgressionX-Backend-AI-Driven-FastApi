from pydantic import BaseModel, EmailStr, Field


class LoginSchema(BaseModel):
    email: EmailStr = Field(..., description="Email of user")
    password: str = Field(..., description="Password of user", min_length=8)

class RefreshSchema(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken", description="Refresh token")

    class Config:
        validate_by_name = True

class TokenSchema(BaseModel):
    access_token: str = Field(..., alias="accessToken", description="Access token")
    refresh_token: str = Field(..., alias="refreshToken", description="Refresh token")
    token_type: str = Field(default="bearer", alias="tokenType")
    # True once the user has supplied age/weight/height/goal/gender. Google
    # signup flow sets this false on first login so the frontend can route
    # the user to /profile/complete. Email+password signups always set true.
    is_profile_complete: bool = Field(True, alias="isProfileComplete")

    class Config:
        validate_by_name = True


class GoogleLoginSchema(BaseModel):
    """The Google ID token (a JWT) returned by Google Identity Services on
    the frontend, POSTed here for server-side verification."""
    credential: str = Field(..., description="Google ID token (JWT)")

