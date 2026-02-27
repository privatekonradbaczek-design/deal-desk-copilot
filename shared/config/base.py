from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Base configuration inherited by all services.

    Values are loaded from environment variables.
    No defaults for secrets — missing values raise ValidationError at startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    service_name: str = Field(..., description="Service identifier")
    service_port: int = Field(default=8000, ge=1024, le=65535)
    app_version: str = Field(default="0.1.0")
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    # PostgreSQL
    database_url: SecretStr = Field(..., description="asyncpg DSN")
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)

    # Redpanda
    redpanda_bootstrap_servers: str = Field(..., description="Comma-separated broker list")

    # Azure OpenAI
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: SecretStr = Field(default=SecretStr(""))
    azure_openai_api_version: str = Field(default="2024-08-01-preview")
    azure_openai_chat_deployment: str = Field(default="gpt-4o")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-ada-002")
    azure_openai_embedding_dimensions: int = Field(default=1536)
