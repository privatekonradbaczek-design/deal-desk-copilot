from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.documents import Citation, RetrievedChunk


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1, max_length=4096)
    tenant_id: str = Field(min_length=1, max_length=255)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    tenant_id: str
    chunks: list[RetrievedChunk]
    has_context: bool
    refusal_reason: str | None = None

    @classmethod
    def empty(cls, query: str, tenant_id: str, reason: str) -> "RetrievalResult":
        return cls(
            query=query,
            tenant_id=tenant_id,
            chunks=[],
            has_context=False,
            refusal_reason=reason,
        )
