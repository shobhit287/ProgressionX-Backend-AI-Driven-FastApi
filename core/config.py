from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    API_PREFIX: str = "/api/v1"
    GROQ_API_KEY: str = ""
    PORTAL_URL: str
    ENV: str = "development"

    # Superadmin seed
    SUPERADMIN_EMAIL: str = ""
    SUPERADMIN_PASSWORD: str = ""

    # SMTP / email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "ProgressionX"
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
