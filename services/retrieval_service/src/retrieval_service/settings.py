from __future__ import annotations

from pydantic import Field
from shared.config.base import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "retrieval_service"

    retrieval_similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    retrieval_top_k: int = Field(default=5, ge=1, le=20)
