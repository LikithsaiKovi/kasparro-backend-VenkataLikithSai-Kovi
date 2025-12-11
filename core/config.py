from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="Kasparro ETL")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        env="DATABASE_URL",
    )
    api_source_key: str = Field(default="REPLACE_ME", env="API_SOURCE_KEY")
    csv_path: str = Field(default="data/sample.csv", env="CSV_PATH")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


