from __future__ import annotations
from typing import Any, Dict, List
from django.db import connection
from workout.services.retriever import retrieve_exercises

DEFAULT_K = 80

def build_candidate_pack(profile: Dict[str, Any], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal = profile.get("goal", "hypertrophy")
    focus = profile.get("focus_muscles", [])
    base_muscles = focus[:] if focus else ["chest", "back", "quadriceps", "hamstrings", "shoulders", "arms", "core"]

    per_muscle = max(10, DEFAULT_K // max(1, len(base_muscles)))
    candidates: List[Dict[str, Any]] = []
    seen = set()

    for m in base_muscles:
        semantic_q = f"{goal} exercise for {m}"
        objs = retrieve_exercises(q=semantic_q, muscles=[m], limit=per_muscle, use_semantic=True)

        for ex in objs:
            if ex.id in seen:
                continue
            seen.add(ex.id)
            candidates.append({
                "id": ex.id,
                "title": ex.title,
                "muscle_groups": ex.muscle_groups or [],
                "image_url": ex.image_url,
                "image_file": ex.image_file,
                "score": 1.0,
                "reason": f"semantic+muscle:{m}",
            })

    if len(candidates) < 30:
        objs = retrieve_exercises(q=f"{goal} workout exercise", muscles=[], limit=50, use_semantic=True)
        for ex in objs:
            if ex.id in seen:
                continue
            seen.add(ex.id)
            candidates.append({
                "id": ex.id,
                "title": ex.title,
                "muscle_groups": ex.muscle_groups or [],
                "image_url": ex.image_url,
                "image_file": ex.image_file,
                "score": 0.5,
                "reason": "semantic_fallback_pool",
            })

    return candidates[:DEFAULT_K]
