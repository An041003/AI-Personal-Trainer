from __future__ import annotations
from typing import Any, Dict, List

def enrich_plan(draft_plan: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    lookup = {c["id"]: c for c in candidates}
    days_out = []

    for d in draft_plan.get("days", []):
        ex_out = []
        for ex in d.get("exercises", []):
            eid = ex["exercise_id"]
            meta = lookup.get(eid, {})
            ex_out.append({
                **ex,
                "title": meta.get("title"),
                "muscle_groups": meta.get("muscle_groups", []),
                "image_url": meta.get("image_url"),
                "image_file": meta.get("image_file"),
            })
        days_out.append({"day": d.get("day"), "exercises": ex_out})

    return {**draft_plan, "days": days_out}
