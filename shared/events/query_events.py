from __future__ import annotations

from uuid import UUID

from shared.events.base import BaseEvent


class QueryRequestedEvent(BaseEvent):
    session_id: UUID
    query_text_hash: str
    user_id: str

    @property
    def topic(self) -> str:
        return "query.requested"


class QueryCompletedEvent(BaseEvent):
    session_id: UUID
    decision_id: UUID
    user_id: str
    response_classification: str
    prompt_tokens: int
    completion_tokens: int
    model_id: str
    chunk_ids_used: list[UUID]

    @property
    def topic(self) -> str:
        return "query.completed"


class QueryRefusedEvent(BaseEvent):
    session_id: UUID
    user_id: str
    refusal_reason: str
    refusal_code: str

    @property
    def topic(self) -> str:
        return "query.refused"
