from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Request

from agent_service.domain.models import QueryRequest, QueryResponse
from agent_service.graph.state import AgentState, AgentStep
from shared.logging.config import bind_request_context

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, tags=["agent"])
async def query(request: Request, body: QueryRequest) -> QueryResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    session_id = str(uuid.uuid4())

    bind_request_context(
        correlation_id=correlation_id,
        user_id=body.user_id,
        tenant_id=body.tenant_id,
    )

    log = logger.bind(session_id=session_id, correlation_id=correlation_id)
    log.info("agent.session.started", query_length=len(body.query))

    initial_state: AgentState = {
        "session_id": session_id,
        "correlation_id": correlation_id,
        "tenant_id": body.tenant_id,
        "user_id": body.user_id,
        "query": body.query,
        "guardrail_passed": None,
        "guardrail_refusal_code": None,
        "retrieved_chunks": [],
        "has_context": False,
        "answer": None,
        "citations": [],
        "synthesis_attempts": 0,
        "citation_verified": False,
        "current_step": AgentStep.INIT,
        "error_message": None,
        "refusal_reason": None,
    }

    graph = request.app.state.graph
    final_state: AgentState = await graph.ainvoke(initial_state)

    step = final_state["current_step"]
    is_done = step == AgentStep.DONE

    log.info(
        "agent.session.completed",
        final_step=step,
        has_answer=bool(final_state.get("answer")),
        citation_count=len(final_state.get("citations", [])),
    )

    return QueryResponse(
        session_id=session_id,
        correlation_id=correlation_id,
        answer=final_state.get("answer") if is_done else None,
        citations=final_state.get("citations", []) if is_done else [],
        response_classification="FACTUAL_WITH_CITATIONS" if is_done else "REFUSED",
        refusal_reason=final_state.get("refusal_reason"),
    )
