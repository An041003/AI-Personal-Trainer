from __future__ import annotations

from typing import Any, Dict

from workout.orchestration.state import SharedState
from workout.langgraph.workout_graph import run_workout_planning_graph


def run_workout_planning_pipeline(raw_input: Dict[str, Any]) -> SharedState:
    """
    Phase 2: Orchestration chuyển sang LangGraph.
    Giữ nguyên signature và kiểu return để các view/API không phải đổi.
    """
    return run_workout_planning_graph(raw_input)
