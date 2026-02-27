from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class BaseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID
    timestamp_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    schema_version: str = "1.0"
    tenant_id: str

    @property
    def topic(self) -> str:
        raise NotImplementedError("Subclasses must define topic property.")
