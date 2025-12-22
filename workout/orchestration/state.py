from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class SharedState:
    request_id: str
    profile: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    candidates: List[Dict[str, Any]] = field(default_factory=list)

    draft_plan: Optional[Dict[str, Any]] = None
    final_plan: Optional[Dict[str, Any]] = None

    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    audit: Dict[str, Any] = field(default_factory=lambda: {"events": [], "iterations": []})

    def log(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.audit["events"].append({"name": name, "payload": payload or {}})
