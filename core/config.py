from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    API_PREFIX: str = "/api/v1"
    GEMINI_API_KEY: str = ""
    PORTAL_URL: str 

    class Config:
        env_file = ".env"

settings = Settings()
