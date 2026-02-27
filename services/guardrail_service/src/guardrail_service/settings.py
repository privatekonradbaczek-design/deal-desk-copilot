from __future__ import annotations

from pydantic import Field
from shared.config.base import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "guardrail_service"

    injection_score_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    max_query_length: int = Field(default=4096)
