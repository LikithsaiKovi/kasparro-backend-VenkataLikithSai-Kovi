from functools import lru_cache
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="Kasparro ETL")
    database_url: str = Field(
        default="",
        env="DATABASE_URL",
    )
    api_source_key: str = Field(default="REPLACE_ME", env="API_SOURCE_KEY")
    csv_path: str = Field(default="data/sample.csv", env="CSV_PATH")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    scheduler_token: str | None = Field(default=None, env="SCHEDULER_TOKEN")

    @field_validator("database_url")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """
        Ensure DATABASE_URL uses asyncpg driver for async SQLAlchemy.
        Railway and other platforms often provide postgresql:// URLs,
        but we need postgresql+asyncpg:// for async operations.
        """
        if not v or v.strip() == "":
            raise ValueError(
                "DATABASE_URL environment variable is required but not set. "
                "Please set it to your PostgreSQL connection string. "
                "For Railway, use the DATABASE_URL from your PostgreSQL service."
            )
        
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            # Convert postgresql:// to postgresql+asyncpg://
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://") and "+asyncpg" not in v:
            # Handle postgres:// shorthand as well
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
