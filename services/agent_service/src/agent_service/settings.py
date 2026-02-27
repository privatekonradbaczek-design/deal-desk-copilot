from __future__ import annotations

from pydantic import Field
from shared.config.base import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "agent_service"

    retrieval_service_url: str = Field(default="http://retrieval_service:8000")
    guardrail_service_url: str = Field(default="http://guardrail_service:8000")

    retrieval_top_k: int = Field(default=5)
    retrieval_similarity_threshold: float = Field(default=0.75)
    max_context_tokens: int = Field(default=8192)
    max_synthesis_retries: int = Field(default=2)
