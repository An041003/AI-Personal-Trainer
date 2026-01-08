from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from typing_extensions import TypedDict
from langchain_core.documents import Document
from dataclasses import dataclass, field

from backend.core.state import BaseGraphState, BaseResult, generate_request_id


class WorkoutGraphState(BaseGraphState, total=False):
    """Workout-specific state"""
    profile: Dict[str, Any]
    constraints: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    candidate_ids: Set[int]
    draft_plan: Optional[Dict[str, Any]]
    documents: List[Document]
    final_plan: Optional[Dict[str, Any]]
    internal_goal: Optional[Dict[str, Any]] = None

@dataclass
class WorkoutPlanResult(BaseResult):
    """Workout plan result"""
    profile: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    draft_plan: Optional[Dict[str, Any]] = None
    final_plan: Optional[Dict[str, Any]] = None
    internal_goal: Optional[Dict[str, Any]] = None

def init_workout_state(raw_input: Dict[str, Any]) -> WorkoutGraphState:
    """Initialize workout graph state"""
    return WorkoutGraphState(
        request_id=generate_request_id(),
        raw_input=raw_input,
        profile={},
        constraints={},
        candidates=[],
        candidate_ids=set(),
        iteration=0,
        max_iter=2,
        draft_plan=None,
        issues=[],
        warnings=[],
        documents=[],
        final_plan=None,
        audit={"events": [], "iterations": []},
    )


def to_workout_result(state: WorkoutGraphState) -> WorkoutPlanResult:
    """Convert graph state to result"""
    return WorkoutPlanResult(
        request_id=state["request_id"],
        profile=state.get("profile", {}),
        constraints=state.get("constraints", {}),
        candidates=state.get("candidates", []),
        draft_plan=state.get("draft_plan"),
        final_plan=state.get("final_plan"),
        internal_goal=state.get("internal_goal"),
        issues=state.get("issues", []),
        warnings=state.get("warnings", []),
        audit=state.get("audit", {"events": [], "iterations": []}),
    )


