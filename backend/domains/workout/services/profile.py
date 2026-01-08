from __future__ import annotations

from typing import Any, Dict, List, Optional


def _split_csv(s: str) -> List[str]:
    return [x.strip().lower() for x in (s or "").split(",") if x.strip()]


def _maybe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _maybe_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


# ------------------------------
# training_days canonicalization
# ------------------------------
_TRAINING_DAY_ALIASES = {
    "mon": "mon",
    "monday": "mon",
    "tue": "tue",
    "tues": "tue",
    "tuesday": "tue",
    "wed": "wed",
    "weds": "wed",
    "wednesday": "wed",
    "thu": "thu",
    "thur": "thu",
    "thurs": "thu",
    "thursday": "thu",
    "fri": "fri",
    "friday": "fri",
    "sat": "sat",
    "saturday": "sat",
    "sun": "sun",
    "sunday": "sun",
}

_ALLOWED_TRAINING_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_TRAINING_DAY_ORDER = {d: i for i, d in enumerate(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])}


def _default_training_days(days_per_week: int) -> List[str]:
    presets = {
        1: ["mon"],
        2: ["mon", "thu"],
        3: ["mon", "wed", "fri"],
        4: ["mon", "tue", "thu", "fri"],
        5: ["mon", "tue", "wed", "thu", "fri"],
        6: ["mon", "tue", "wed", "thu", "fri", "sat"],
        7: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    }
    return presets.get(int(days_per_week), ["mon", "wed", "fri"])


def _canonicalize_training_days(raw_td: Any) -> Optional[List[str]]:
    if raw_td is None:
        return None
    if not isinstance(raw_td, list):
        return None
    out: List[str] = []
    for x in raw_td:
        s = str(x or "").strip().lower()
        if not s:
            continue
        out.append(_TRAINING_DAY_ALIASES.get(s, s))
    return out


def _validate_training_days(td: List[str], expected_len: int) -> List[str]:
    errs: List[str] = []
    if len(td) != int(expected_len):
        errs.append(f"training_days phải có đúng {expected_len} phần tử")
        return errs
    if len(set(td)) != len(td):
        errs.append("training_days phải unique")
    bad = [d for d in td if d not in _ALLOWED_TRAINING_DAYS]
    if bad:
        errs.append(f"training_days chứa giá trị không hợp lệ: {bad}")
    return errs


def normalize_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bước 0 input tối thiểu:
      - goal_text
      - days_per_week
      - session_minutes
    Optional:
      - training_days (list mon..sun)  # NEW
      - sex/height/weight/waist/hip/chest
      - experience
      - equipment (CSV string)
      - seed
      - user_id (cache)
    """
    # Backward-compat fallback: nếu client cũ vẫn gửi `goal` thay vì `goal_text`
    goal_text = (raw.get("goal_text") or "").strip()
    if not goal_text:
        goal_text = (raw.get("goal") or "").strip()  # legacy
    goal_text = goal_text.strip()

    # Parse required fields
    days = _maybe_int(raw.get("days_per_week"))
    minutes = _maybe_int(raw.get("session_minutes"))
    if days is None:
        raise ValueError("days_per_week is required")
    if minutes is None:
        raise ValueError("session_minutes is required")

    seed = _maybe_int(raw.get("seed"))

    sex = (raw.get("sex") or "").strip().lower() or None
    experience = (raw.get("experience") or "").strip().lower() or None

    equipment_list = _split_csv(raw.get("equipment") or "")

    # NEW: training_days
    td = _canonicalize_training_days(raw.get("training_days"))
    if not td:
        td = _default_training_days(days)
    else:
        td_errs = _validate_training_days(td, expected_len=days)
        if td_errs:
            # Policy: fallback default nếu client gửi sai
            td = _default_training_days(days)

    # sort deterministic
    td = sorted(td, key=lambda d: _TRAINING_DAY_ORDER.get(d, 999))

    return {
        "user_id": raw.get("user_id"),  # optional, dùng cho cache
        "goal_text": goal_text,
        "days_per_week": days,
        "session_minutes": minutes,

        # NEW
        "training_days": td,

        # optional metrics
        "sex": sex,
        "height": _maybe_float(raw.get("height")),
        "weight": _maybe_float(raw.get("weight")),
        "waist": _maybe_float(raw.get("waist")),
        "hip": _maybe_float(raw.get("hip")),
        "chest": _maybe_float(raw.get("chest")),

        "experience": experience,
        "equipment": equipment_list,

        # internal_goal sẽ được set ở bước Intent → Internal Goal (chưa implement thì None)
        "internal_goal": raw.get("internal_goal"),

        "seed": seed,
    }
