from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = "csv,xlsx"

    USE_SPARK_ABOVE_MB: int = 500

    TEMP_DIR: str = "./data/temp"

    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
