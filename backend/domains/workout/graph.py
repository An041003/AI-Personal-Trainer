from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import START, END, StateGraph

from backend.core.audit import append_event
from backend.domains.workout.state import (
    WorkoutGraphState,
    init_workout_state,
    to_workout_result,
    WorkoutPlanResult,
)

from backend.domains.workout import nodes as workout_nodes


def build_workout_graph() -> StateGraph:
    """Build workout planning graph (LangGraph StateGraph)."""
    builder = StateGraph(WorkoutGraphState)

    # Nodes (logic nằm trong nodes.py)
    builder.add_node("profile", workout_nodes.node_profile)
    builder.add_node("constraints", workout_nodes.node_constraints)
    builder.add_node("intent", workout_nodes.node_intent)        # <-- node intent chuẩn
    builder.add_node("retrieval", workout_nodes.node_retrieval)
    builder.add_node("plan", workout_nodes.node_plan)
    builder.add_node("evaluate", workout_nodes.node_evaluate)
    builder.add_node("enrich", workout_nodes.node_enrich)

    # Edges
    builder.add_edge(START, "profile")
    builder.add_edge("profile", "constraints")
    builder.add_edge("constraints", "intent")
    builder.add_edge("intent", "retrieval")
    builder.add_edge("retrieval", "plan")
    builder.add_edge("plan", "evaluate")

    # Conditional routing sau evaluate
    builder.add_conditional_edges(
        "evaluate",
        workout_nodes.route_after_eval,
        {
            "plan": "plan",      # retry
            "enrich": "enrich",  # finalize
        },
    )
    builder.add_edge("enrich", END)

    return builder.compile()


_WORKOUT_GRAPH: StateGraph | None = None


def get_workout_graph() -> StateGraph:
    """Lazy-load singleton graph instance."""
    global _WORKOUT_GRAPH
    if _WORKOUT_GRAPH is None:
        _WORKOUT_GRAPH = build_workout_graph()
    return _WORKOUT_GRAPH


def run_workout_planning_pipeline(raw_input: Dict[str, Any]) -> WorkoutPlanResult:
    """Main entry point cho workout planning."""
    init_state = init_workout_state(raw_input)
    init_state["audit"] = append_event(
        init_state.get("audit", {"events": [], "iterations": []}),
        "pipeline_start",
        {"raw_input": raw_input},
    )

    graph = get_workout_graph()
    final_state = graph.invoke(init_state)
    return to_workout_result(final_state)
