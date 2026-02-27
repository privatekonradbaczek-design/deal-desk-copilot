from __future__ import annotations

from pydantic import Field
from shared.config.base import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "ingestion_service"

    storage_base_path: str = Field(default="/app/storage")
    max_document_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_content_types: list[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]
    )
