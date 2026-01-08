# backend/domains/workout/contract.py
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Tuple


# ============================================================
# Taxonomy / Enums (single source of truth)
# ============================================================

MUSCLE_TAXONOMY: Tuple[str, ...] = (
    "chest",
    "shoulders",
    "triceps",
    "back",
    "biceps",
    "quadriceps",
    "hamstrings",
    "hips",      # canonical (replaces glutes)
    "calves",
    "core",
)
MUSCLE_TAXONOMY_SET = set(MUSCLE_TAXONOMY)

GOAL_STYLE_ENUM: Tuple[str, ...] = (
    "health",
    "general_fitness",
    "fat_loss",
    "body_recomposition",
    "hypertrophy",
    "strength",
    "endurance",
    "athletic_performance",
    "mobility_flexibility",
    "posture_stability",
    "rehab_prevention",
    "mixed",
)
GOAL_STYLE_ENUM_SET = set(GOAL_STYLE_ENUM)

# Optional: dùng cho UI/autocomplete, không enforce cứng
PRIORITY_TARGET_SUGGESTIONS: Tuple[str, ...] = (
    "abs",
    "hips",
    "upper chest",
    "v taper",
    "shoulder caps",
    "arms",
    "back thickness",
    "posture",
    "mobility",
)

TRAINING_DAY_ENUM: Tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TRAINING_DAY_SET = set(TRAINING_DAY_ENUM)

# Canonicalization aliases (apply BEFORE strict validation)
MUSCLE_ALIASES = {
    "glutes": "hips",
}


# ============================================================
# Helpers
# ============================================================

def canonicalize_muscle(m: str) -> str:
    m2 = (m or "").strip().lower()
    return MUSCLE_ALIASES.get(m2, m2)


def is_valid_training_day(day: str) -> bool:
    return (day or "").strip().lower() in TRAINING_DAY_SET


def is_valid_muscle(muscle: str) -> bool:
    return (muscle or "").strip().lower() in MUSCLE_TAXONOMY_SET


def is_valid_goal_style(goal_style: str) -> bool:
    return (goal_style or "").strip().lower() in GOAL_STYLE_ENUM_SET


def _as_day_items(weekly_focus_by_day: Any) -> list[dict]:
    """Coerce weekly_focus_by_day to list[dict] best-effort, for callers that want to pre-normalize."""
    if weekly_focus_by_day is None:
        return []
    if isinstance(weekly_focus_by_day, list):
        return [x for x in weekly_focus_by_day if isinstance(x, dict)]
    return []


# ============================================================
# Validation for LLM Intent → Internal Goal output
# ============================================================

def validate_priority_muscles(priority_muscles: Any) -> List[str]:
    """Validate list muscles; canonicalize glutes->hips before checking taxonomy."""
    errors: List[str] = []
    if priority_muscles is None:
        return errors
    if not isinstance(priority_muscles, list):
        return ["priority_muscles phải là danh sách."]

    for i, m in enumerate(priority_muscles):
        mm = canonicalize_muscle(str(m))
        if not is_valid_muscle(mm):
            errors.append(
                f"priority_muscles[{i}] không hợp lệ (={m}). "
                f"Chỉ được dùng taxonomy muscles: {list(MUSCLE_TAXONOMY)}"
            )
    return errors


def validate_training_days(training_days: Any, days_per_week: Optional[int] = None) -> List[str]:
    """Validate training_days; optional field. If days_per_week provided -> enforce exact length."""
    errors: List[str] = []
    if training_days is None:
        return errors  # optional

    if not isinstance(training_days, list):
        return ["training_days phải là list"]

    td = [str(x).strip().lower() for x in training_days]

    if days_per_week is not None and len(td) != int(days_per_week):
        errors.append(f"training_days phải có đúng {days_per_week} phần tử")

    if len(set(td)) != len(td):
        errors.append("training_days phải unique")

    for x in td:
        if not is_valid_training_day(x):
            errors.append(f"training_day không hợp lệ: {x}")
    return errors


def validate_weekly_focus_by_day(
    weekly_focus_by_day: Any,
    days_per_week: Optional[int] = None,
) -> List[str]:
    """Validate NEW shape: [{training_day, focus:[{muscle, rank}]}]."""
    if weekly_focus_by_day is None:
        return []
    if not isinstance(weekly_focus_by_day, list):
        return ["weekly_focus_by_day phải là list"]

    errors: List[str] = []

    if days_per_week is not None and len(weekly_focus_by_day) != int(days_per_week):
        errors.append(f"weekly_focus_by_day phải có đúng {days_per_week} ngày")

    seen_days: set[str] = set()

    for di, day_obj in enumerate(weekly_focus_by_day):
        if not isinstance(day_obj, dict):
            errors.append(f"weekly_focus_by_day[{di}] phải là object")
            continue

        td = str(day_obj.get("training_day") or "").strip().lower()
        focus = day_obj.get("focus")

        if not is_valid_training_day(td):
            errors.append(f"weekly_focus_by_day[{di}].training_day không hợp lệ: {td}")
        else:
            if td in seen_days:
                errors.append(f"training_day bị trùng: {td}")
            seen_days.add(td)

        if not isinstance(focus, list):
            errors.append(f"weekly_focus_by_day[{di}].focus phải là list")
            continue

        seen_rank: set[int] = set()
        seen_muscle: set[str] = set()

        for fi, item in enumerate(focus):
            if not isinstance(item, dict):
                errors.append(f"weekly_focus_by_day[{di}].focus[{fi}] phải là object")
                continue

            m_raw = str(item.get("muscle") or "")
            m = canonicalize_muscle(m_raw)
            r = item.get("rank")

            if not is_valid_muscle(m):
                errors.append(f"day[{di}].focus[{fi}].muscle không hợp lệ: {m_raw}")
            if not isinstance(r, int) or not (1 <= r <= 10):
                errors.append(f"day[{di}].focus[{fi}].rank không hợp lệ: {r}")

            if isinstance(r, int):
                if r in seen_rank:
                    errors.append(f"day[{di}] bị trùng rank: {r}")
                seen_rank.add(r)

            if m:
                if m in seen_muscle:
                    errors.append(f"day[{di}] bị trùng muscle: {m}")
                seen_muscle.add(m)

    return errors


def validate_intent_internal_goal(
    payload: Mapping[str, Any],
    days_per_week: Optional[int] = None,
) -> List[str]:
    """
    Validate tối thiểu cho output LLM Intent → Internal Goal.

    payload expected keys:
      - goal_style
      - priority_targets
      - priority_muscles
      - training_days                  (optional)
      - weekly_focus_by_day            NEW shape: [{training_day, focus:[{muscle, rank}]}]
      - risk_notes (optional)
    """
    errors: List[str] = []

    goal_style = payload.get("goal_style")
    if not is_valid_goal_style(goal_style):
        errors.append(
            f"goal_style không hợp lệ (={goal_style}). "
            f"Giá trị hợp lệ: {list(GOAL_STYLE_ENUM)}"
        )

    errors.extend(validate_priority_muscles(payload.get("priority_muscles")))

    errors.extend(validate_training_days(payload.get("training_days"), days_per_week=days_per_week))

    errors.extend(
        validate_weekly_focus_by_day(
            payload.get("weekly_focus_by_day"),
            days_per_week=days_per_week,
        )
    )

    # Cross-check: if both provided, enforce same set of days
    training_days = payload.get("training_days")
    weekly_focus_by_day = payload.get("weekly_focus_by_day")
    if isinstance(training_days, list) and isinstance(weekly_focus_by_day, list):
        td = [str(x).strip().lower() for x in training_days]
        wfd: list[str] = []
        for item in weekly_focus_by_day:
            if isinstance(item, dict):
                wfd.append(str(item.get("training_day") or "").strip().lower())

        if td and wfd:
            # only check when both lists look unique-ish to avoid noisy duplicate errors
            if len(set(td)) == len(td) and len(set(wfd)) == len(wfd):
                if set(td) != set(wfd):
                    errors.append(
                        "training_days và weekly_focus_by_day.training_day phải khớp nhau (cùng tập ngày)."
                    )

                if days_per_week is not None:
                    if len(td) != int(days_per_week) or len(wfd) != int(days_per_week):
                        errors.append(
                            "training_days và weekly_focus_by_day phải có đúng số ngày bằng days_per_week."
                        )

    return errors
