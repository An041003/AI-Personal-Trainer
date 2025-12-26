from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Set
from typing_extensions import TypedDict
from langchain_core.documents import Document


class WorkoutGraphState(TypedDict, total=False):
    # Input
    request_id: str
    raw_input: Dict[str, Any]

    # Core data
    profile: Dict[str, Any]
    constraints: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    candidate_ids: Set[int]

    # Planning loop
    iteration: int          # 0..max_iter
    max_iter: int           # = constraints["max_repair_iterations"] (default 2)
    draft_plan: Optional[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    warnings: List[str]
    documents: List[Document]

    # Output
    final_plan: Optional[Dict[str, Any]]

    # Audit
    audit: Dict[str, Any]


def init_graph_state(raw_input: Dict[str, Any]) -> WorkoutGraphState:
    return WorkoutGraphState(
        request_id=str(uuid.uuid4()),
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


def append_event(audit: Dict[str, Any], name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    events = list(audit.get("events", []))
    events.append({"name": name, "payload": payload or {}})
    new_audit = dict(audit)
    new_audit["events"] = events
    return new_audit


def append_iteration(audit: Dict[str, Any], iteration: int) -> Dict[str, Any]:
    iters = list(audit.get("iterations", []))
    iters.append({"iteration": iteration})
    new_audit = dict(audit)
    new_audit["iterations"] = iters
    return new_audit
    documents: List[Document]