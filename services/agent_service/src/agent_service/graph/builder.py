from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph
from openai import AsyncAzureOpenAI

from agent_service.graph.nodes import (
    node_guardrail_check,
    node_retrieve,
    node_synthesize,
    node_verify_citations,
)
from agent_service.graph.state import AgentState, AgentStep
from agent_service.settings import Settings


def route_after_guardrail(state: AgentState) -> str:
    return AgentStep.RETRIEVAL if state["guardrail_passed"] else AgentStep.REFUSED


def route_after_retrieval(state: AgentState) -> str:
    return AgentStep.SYNTHESIS if state["has_context"] else AgentStep.REFUSED


def route_after_verification(state: AgentState) -> str:
    step = state["current_step"]
    if step == AgentStep.DONE:
        return END
    if step == AgentStep.SYNTHESIS:
        return AgentStep.SYNTHESIS
    return AgentStep.REFUSED


def build_graph(settings: Settings, openai_client: AsyncAzureOpenAI) -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node(
        AgentStep.GUARDRAIL_CHECK,
        partial(node_guardrail_check, settings=settings),
    )
    graph.add_node(
        AgentStep.RETRIEVAL,
        partial(node_retrieve, settings=settings),
    )
    graph.add_node(
        AgentStep.SYNTHESIS,
        partial(node_synthesize, openai_client=openai_client, settings=settings),
    )
    graph.add_node(
        AgentStep.CITATION_VERIFICATION,
        partial(node_verify_citations, settings=settings),
    )
    graph.add_node(AgentStep.REFUSED, lambda state: {**state, "current_step": AgentStep.REFUSED})

    graph.add_edge(START, AgentStep.GUARDRAIL_CHECK)
    graph.add_conditional_edges(AgentStep.GUARDRAIL_CHECK, route_after_guardrail)
    graph.add_conditional_edges(AgentStep.RETRIEVAL, route_after_retrieval)
    graph.add_edge(AgentStep.SYNTHESIS, AgentStep.CITATION_VERIFICATION)
    graph.add_conditional_edges(AgentStep.CITATION_VERIFICATION, route_after_verification)
    graph.add_edge(AgentStep.REFUSED, END)

    return graph.compile()
