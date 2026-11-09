from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from src.agent.nodes import (
    decide_node,
    generate_node,
    grade_node,
    retrieve_node,
    rewrite_node,
)
from src.agent.state import AgentState


def _after_grade(state: AgentState) -> Literal["generate", "rewrite"]:
    if state.get("grade_passed"):
        return "generate"
    iterations = int(state.get("iterations") or 0)
    max_loops = int(state.get("max_loops") or 1)
    if iterations < max_loops:
        return "rewrite"
    return "generate"


def build_agent_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("decide", decide_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade", grade_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("decide")
    graph.add_edge("decide", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", _after_grade, {"generate": "generate", "rewrite": "rewrite"})
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)
    return graph.compile()
