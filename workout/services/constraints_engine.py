from __future__ import annotations
from typing import Dict, Any

def build_constraints(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "max_repair_iterations": 2,
        "max_exercises_per_day": 6,
        "max_repeat_same_exercise_per_week": 1,
    }
