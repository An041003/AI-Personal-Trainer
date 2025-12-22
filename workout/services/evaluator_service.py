from __future__ import annotations
from typing import Any, Dict, List, Set

def _estimate_minutes(day: Dict[str, Any]) -> int:
    total = 0.0
    for ex in day.get("exercises", []):
        sets = int(ex.get("sets", 0))
        rest = float(ex.get("rest_sec", 0)) / 60.0
        total += sets * (1.0 + rest)
    return int(round(total))

def evaluate_plan(
    draft_plan: Dict[str, Any],
    candidate_ids: Set[int],
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # id-only
    for d in draft_plan.get("days", []):
        for ex in d.get("exercises", []):
            eid = ex.get("exercise_id")
            if eid not in candidate_ids:
                issues.append({"type": "invalid_exercise_id", "detail": f"exercise_id={eid} không nằm trong candidate pack"})

    # tối thiểu số bài/buổi
    for d in draft_plan.get("days", []):
        if len(d.get("exercises", [])) < 4:
            issues.append({"type": "too_few_exercises", "detail": f"{d.get('day')} ít hơn 4 bài"})

    # thời lượng
    session_minutes = int(profile.get("session_minutes", 60))
    for d in draft_plan.get("days", []):
        est = _estimate_minutes(d)
        if est > session_minutes:
            warnings.append(f"{d.get('day')} ước tính {est} phút, vượt {session_minutes} phút")

    return {"issues": issues, "warnings": warnings}
