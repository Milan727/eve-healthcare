from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "EVE Healthcare API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database: SQLite default for local zero-config execution; easily overridden with PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./eve_healthcare.db"

    # Security
    SECRET_KEY: str = "eve-healthcare-super-secret-jwt-signing-key-change-in-prod-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Logging & Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Webhook Secret (optional verification)
    WEBHOOK_SECRET: str = "eve_webhook_secret_key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
