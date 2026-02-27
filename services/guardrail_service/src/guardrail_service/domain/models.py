from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InputValidationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1, max_length=8192)
    tenant_id: str = Field(min_length=1, max_length=255)


class InputValidationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    injection_score: float
    refusal_code: str | None = None
    matched_patterns: list[str] = []


class OutputValidationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[dict]
    tenant_id: str


class OutputValidationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    refusal_code: str | None = None
    citation_count: int
