from pathlib import Path

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    DATABASE_PATH: str = "/data/catalog.db"
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = Field(default=900, ge=60, le=3600)
    REFRESH_TOKEN_TTL_SECONDS: int = Field(default=604800, ge=3600, le=2592000)

    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Seed admin credentials
    SEED_ADMIN_USERNAME: str = Field(default="admin", pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    SEED_ADMIN_EMAIL: EmailStr = "admin@example.com"
    SEED_ADMIN_PASSWORD: str = Field(default="admin123", min_length=8)

    LOG_LEVEL: str = "INFO"

    @field_validator("DATABASE_PATH")
    @classmethod
    def database_path_parent_must_exist(cls, v: str) -> str:
        """Reject paths whose parent directory does not exist.

        The application cannot create the database file if the parent directory
        is missing; failing here gives a clear error at startup rather than a
        cryptic I/O error on first query.
        """
        parent = Path(v).parent
        if not parent.exists():
            raise ValueError(
                f"DATABASE_PATH parent directory does not exist: {parent}"
            )
        return v

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def cors_origins_no_wildcard(cls, v: str) -> str:
        """Reject wildcard origins.

        Using '*' with credentials is a browser security error and a CSRF
        risk; every origin must be named explicitly.
        """
        for origin in v.split(","):
            if origin.strip() == "*":
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must not contain '*'; "
                    "list explicit origins instead"
                )
        return v
