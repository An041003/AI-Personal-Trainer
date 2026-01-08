from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


def _estimate_minutes(day: Dict[str, Any]) -> int:
    total = 0.0
    for ex in day.get("exercises", []):
        sets = int(ex.get("sets", 0) or 0)
        rest = float(ex.get("rest_sec", 0) or 0) / 60.0
        total += sets * (1.0 + rest)
    return int(round(total))


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _canonicalize_muscle(m: str) -> str:
    m = _norm(m)
    # Backward compatibility
    if m == "glutes":
        return "hips"
    return m


def _extract_training_day_for_plan_day(
    plan_day: Dict[str, Any],
    profile_training_days: Optional[List[str]],
) -> Optional[str]:
    """
    Map a plan day to a training_day token (mon..sun).
    Supports:
      - plan_day["training_day"] == "mon".."sun"
      - plan_day["day"] == "mon".."sun"
      - plan_day["day"] == "Day 1"/"day1"/"1" -> map by index to profile_training_days
    """
    td = _norm(plan_day.get("training_day"))
    if td:
        return td

    day = _norm(plan_day.get("day"))
    if day in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}:
        return day

    idx = None
    if day.startswith("day"):
        # "day 1", "day1"
        s = day.replace("day", "").strip()
        if s.isdigit():
            idx = int(s) - 1
    elif day.isdigit():
        idx = int(day) - 1

    if idx is not None and profile_training_days and 0 <= idx < len(profile_training_days):
        return _norm(profile_training_days[idx])

    return None


def _build_rank1_muscles_by_training_day(internal_goal: Any) -> Dict[str, Set[str]]:
    """
    internal_goal expected shape:
      weekly_focus_by_day: [{training_day, focus:[{muscle, rank}]}]
    Returns: {"mon": {"back"}, ...}
    """
    out: Dict[str, Set[str]] = {}
    if not isinstance(internal_goal, dict):
        return out

    w = internal_goal.get("weekly_focus_by_day")
    if not isinstance(w, list):
        return out

    for item in w:
        if not isinstance(item, dict):
            continue
        td = _norm(item.get("training_day"))
        focus = item.get("focus")
        if not td or not isinstance(focus, list):
            continue

        rank1: Set[str] = set()
        for f in focus:
            if not isinstance(f, dict):
                continue
            if f.get("rank") == 1:
                m = _canonicalize_muscle(str(f.get("muscle") or ""))
                if m:
                    rank1.add(m)

        out[td] = rank1

    return out


def _build_primary_muscle_lookup(candidates: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    Build lookup: exercise_id -> primary_muscle from candidate pack.
    Convention: candidates[i]["muscle_groups"][0] is primary.
    """
    lookup: Dict[int, str] = {}
    for c in candidates or []:
        try:
            eid = int(c.get("id"))
        except Exception:
            continue

        muscles = c.get("muscle_groups") or []
        primary = muscles[0] if muscles else ""
        lookup[eid] = _canonicalize_muscle(primary)
    return lookup


def evaluate_plan(
    draft_plan: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluation policy (updated):
      - Validate exercise_id must be within candidate pack
      - Respect min/max exercises per day from constraints
      - Duration warning if estimate > session_minutes
      - Rank1 is ONLY a muscle-level concept in weekly_focus_by_day.
        We DO NOT cap the number of exercises hitting rank1 muscle.
      - Optional warning if a day has 0 exercises whose primary muscle matches rank1 muscle of that day.
        Primary muscle is inferred from candidate pack by exercise_id (preferred),
        or from fields in plan exercise (fallback).
    """
    issues: List[Dict[str, Any]] = []
    warnings: List[str] = []

    candidate_ids: Set[int] = set()
    for c in candidates or []:
        try:
            candidate_ids.add(int(c.get("id")))
        except Exception:
            continue

    primary_lookup = _build_primary_muscle_lookup(candidates)

    # ------------------------
    # 0) Candidate id-only
    # ------------------------
    for d in draft_plan.get("days", []) or []:
        for ex in d.get("exercises", []) or []:
            eid = ex.get("exercise_id")
            try:
                eid_int = int(eid)
            except Exception:
                issues.append({"type": "invalid_exercise_id", "detail": f"exercise_id không hợp lệ: {eid}"})
                continue

            if eid_int not in candidate_ids:
                issues.append({"type": "invalid_exercise_id", "detail": f"exercise_id={eid_int} không nằm trong candidate pack"})

    # ------------------------
    # 1) Min/Max exercises per day
    # ------------------------
    min_ex = constraints.get("min_exercises_per_day")
    max_ex = constraints.get("max_exercises_per_day")

    try:
        min_ex_n = int(min_ex) if min_ex is not None else None
    except Exception:
        min_ex_n = None

    try:
        max_ex_n = int(max_ex) if max_ex is not None else None
    except Exception:
        max_ex_n = None

    for d in draft_plan.get("days", []) or []:
        n = len(d.get("exercises", []) or [])
        label = d.get("training_day") or d.get("day") or "day"

        if min_ex_n is not None and n < min_ex_n:
            issues.append({"type": "too_few_exercises", "detail": f"{label} ít hơn {min_ex_n} bài (={n})"})
        if max_ex_n is not None and n > max_ex_n:
            issues.append({"type": "too_many_exercises", "detail": f"{label} nhiều hơn {max_ex_n} bài (={n})"})

    # ------------------------
    # 2) Duration warnings
    # ------------------------
    try:
        session_minutes = int(profile.get("session_minutes", 60))
    except Exception:
        session_minutes = 60

    for d in draft_plan.get("days", []) or []:
        est = _estimate_minutes(d)
        if est > session_minutes:
            warnings.append(f"{d.get('day') or d.get('training_day')} ước tính {est} phút, vượt {session_minutes} phút")

    # ------------------------
    # 3) Rank1 focus coverage warning (optional)
    # ------------------------
    internal_goal = profile.get("internal_goal") or {}
    rank1_by_day = _build_rank1_muscles_by_training_day(internal_goal)

    profile_training_days = profile.get("training_days")
    if isinstance(profile_training_days, list):
        profile_training_days = [_norm(x) for x in profile_training_days]
    else:
        profile_training_days = None

    if rank1_by_day:
        for d in draft_plan.get("days", []) or []:
            td = _extract_training_day_for_plan_day(d, profile_training_days)
            if not td:
                continue

            rank1_muscles = rank1_by_day.get(td, set())
            if not rank1_muscles:
                continue

            hit = 0
            for ex in d.get("exercises", []) or []:
                eid = ex.get("exercise_id")
                try:
                    eid_int = int(eid)
                except Exception:
                    continue

                # Prefer explicit plan field if present, else infer by candidate pack
                pm = _canonicalize_muscle(
                    ex.get("primary_muscle") or ex.get("muscle") or ex.get("muscle_group") or primary_lookup.get(eid_int, "")
                )
                if pm and pm in rank1_muscles:
                    hit += 1

            if hit == 0:
                warnings.append(f"{td} không có bài nào thuộc rank 1 muscle. rank1={sorted(list(rank1_muscles))}")

    return {"issues": issues, "warnings": warnings}
