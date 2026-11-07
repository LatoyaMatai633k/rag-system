"""Configuration loaded from environment variables, never source code."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the existing LlamaIndex/OpenRouter pipeline."""

    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    data_dir: Path = Path("data")
    pack_dir: Path = Path("query_rewriting_pack")

    # ``enable_decoding=False`` lets ALLOWED_ORIGINS be the beginner-friendly
    # comma-separated value shown in .env.example instead of JSON.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", enable_decoding=False)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
