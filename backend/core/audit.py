from __future__ import annotations

from typing import Any, Dict, Optional


def append_event(audit: Dict[str, Any], name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Append event to audit trail"""
    events = list(audit.get("events", []))
    events.append({"name": name, "payload": payload or {}})
    return {**audit, "events": events}


def append_iteration(audit: Dict[str, Any], iteration: int) -> Dict[str, Any]:
    """Append iteration to audit trail"""
    iters = list(audit.get("iterations", []))
    iters.append({"iteration": iteration})
    return {**audit, "iterations": iters}


