from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    service: str
    version: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    error_code: str
    message: str
    correlation_id: str | None = None
