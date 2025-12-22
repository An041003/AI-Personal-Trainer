from __future__ import annotations
from typing import Any, Dict, List, Optional

def normalize_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    goal = (raw.get("goal") or "hypertrophy").strip().lower()
    days = int(raw.get("days_per_week"))
    minutes = int(raw.get("session_minutes"))

    focus_raw = (raw.get("focus_muscles") or "").strip().lower()
    focus: List[str] = [x.strip() for x in focus_raw.split(",") if x.strip()]

    seed: Optional[int] = raw.get("seed", None)
    seed = int(seed) if seed is not None else None

    return {
        "goal": goal,
        "days_per_week": days,
        "session_minutes": minutes,
        "focus_muscles": focus,
        "seed": seed,
    }
