from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.documents import Citation


class QueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1, max_length=4096)
    tenant_id: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)


class QueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    correlation_id: str
    answer: str | None
    citations: list[Citation]
    response_classification: str
    refusal_reason: str | None = None
