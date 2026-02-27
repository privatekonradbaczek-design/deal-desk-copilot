from __future__ import annotations

from enum import StrEnum
from typing import TypedDict
from uuid import UUID

from shared.schemas.documents import Citation, RetrievedChunk


class AgentStep(StrEnum):
    INIT = "init"
    GUARDRAIL_CHECK = "guardrail_check"
    RETRIEVAL = "retrieval"
    SYNTHESIS = "synthesis"
    CITATION_VERIFICATION = "citation_verification"
    DONE = "done"
    REFUSED = "refused"
    ERROR = "error"


class AgentState(TypedDict):
    # Identity
    session_id: str
    correlation_id: str
    tenant_id: str
    user_id: str

    # Input
    query: str

    # Guardrail
    guardrail_passed: bool | None
    guardrail_refusal_code: str | None

    # Retrieval
    retrieved_chunks: list[RetrievedChunk]
    has_context: bool

    # Synthesis
    answer: str | None
    citations: list[Citation]
    synthesis_attempts: int

    # Citation verification
    citation_verified: bool

    # Control
    current_step: str
    error_message: str | None
    refusal_reason: str | None
