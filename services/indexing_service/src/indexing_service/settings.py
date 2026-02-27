from __future__ import annotations

from pydantic import Field
from shared.config.base import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "indexing_service"

    storage_base_path: str = Field(default="/app/storage")
    consumer_group_id: str = Field(default="indexing-service-group")
    consumer_topic: str = Field(default="document.uploaded")

    chunk_size_tokens: int = Field(default=512, ge=64, le=2048)
    chunk_overlap_tokens: int = Field(default=64, ge=0, le=256)
