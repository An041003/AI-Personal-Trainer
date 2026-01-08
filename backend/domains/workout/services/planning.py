from __future__ import annotations

import json
import hashlib
from typing import Any, Dict, List, Optional, Set

from langchain_core.documents import Document

from backend.shared.llm import LLMClient
from backend.shared.simple_cache import cache_get, cache_set
from backend.domains.workout.contract import (
    MUSCLE_TAXONOMY,
    GOAL_STYLE_ENUM,
    TRAINING_DAY_ENUM,
    validate_intent_internal_goal,
)
from backend.domains.workout.schemas import IntentInternalGoal


PLAN_CACHE_TTL = 900  # 15 phút
INTENT_CACHE_TTL = 900  # 15 phút


def _format_candidate_lines_from_docs(documents: List[Document], max_items: int = 45) -> str:
    lines: List[str] = []
    for d in documents[:max_items]:
        m = d.metadata or {}
        eid = m.get("id")
        title = m.get("title", "")
        muscles = m.get("muscle_groups") or []
        equipment = m.get("equipment") or []
        level = m.get("level") or ""

        parts = [f"id={eid}", title]

        if muscles:
            parts.append(f"muscles={','.join(map(str, muscles))}")

        if equipment:
            parts.append(f"equip={','.join(map(str, equipment))}")

        if level:
            parts.append(f"level={level}")

        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _format_candidate_lines_fallback(candidates: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for c in candidates:
        parts = [f"id={c['id']}", c.get("title", "")]

        muscles = c.get("muscle_groups") or []
        if muscles:
            mg = ",".join([str(x) for x in muscles])
            parts.append(f"muscles={mg}")

        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _guard_before_llm(
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    min_candidates: int = 20,
) -> Optional[Dict[str, Any]]:
    """
    Hard-guard trước khi gọi LLM để tránh prompt xấu / waste token.
    """
    errors: List[str] = []

    # days_per_week guard
    try:
        days = int(profile.get("days_per_week", 0))
    except Exception:
        days = 0
    if not (1 <= days <= 7):
        errors.append(f"days_per_week không hợp lệ (={days}). Giá trị hợp lệ trong khoảng 1–7.")

    # session_minutes guard
    try:
        minutes = int(profile.get("session_minutes", 0))
    except Exception:
        minutes = 0
    if not (10 <= minutes <= 240):
        errors.append(f"session_minutes không hợp lệ (={minutes}). Giá trị hợp lệ trong khoảng 10–240 phút.")

    # internal_goal guard (nếu đã có output Intent → Internal Goal)
    internal_goal = profile.get("internal_goal")
    if internal_goal:
        internal_errors = validate_intent_internal_goal(internal_goal, days_per_week=days)
        for e in internal_errors:
            errors.append(f"internal_goal không hợp lệ: {e}")

    # max_exercises_per_day guard
    try:
        max_exercises = int(constraints.get("max_exercises_per_day", 0))
    except Exception:
        max_exercises = 0
    if not (1 <= max_exercises <= 20):
        errors.append(f"max_exercises_per_day không hợp lệ (={max_exercises}). Giá trị hợp lệ trong khoảng 1–20.")

    # candidates count guard
    candidate_count = len(candidates or [])
    if candidate_count < min_candidates:
        errors.append(
            (
                f"Không đủ bài tập phù hợp để tạo kế hoạch (tìm được {candidate_count}, "
                f"cần tối thiểu {min_candidates}). Hãy thử giảm bớt bộ lọc hoặc mở rộng nhóm cơ."
            )
        )

    if not errors:
        return None

    return {
        "error_type": "validation_guard_failed",
        "message": "Dữ liệu đầu vào chưa phù hợp để tạo workout plan. Vui lòng điều chỉnh và thử lại.",
        "errors": errors,
        "profile": profile,
        "constraints": constraints,
        "candidate_count": candidate_count,
    }


def _build_intent_prompt(profile: Dict[str, Any]) -> str:
    days = profile.get("days_per_week")
    minutes = profile.get("session_minutes")

    parts: List[str] = []
    parts.append("Nhiệm vụ: phân tích goal_text và chuẩn hóa thành Internal Goal dạng JSON đúng schema.")
    parts.append("")
    parts.append("Input profile:")
    parts.append(json.dumps(profile, ensure_ascii=False))
    parts.append("")

    parts.append("Taxonomy muscles hợp lệ (BẮT BUỘC dùng đúng):")
    parts.append(", ".join(MUSCLE_TAXONOMY))
    parts.append("")
    parts.append("Enum goal_style hợp lệ:")
    parts.append(", ".join(GOAL_STYLE_ENUM))
    parts.append("")
    parts.append("Enum training_days hợp lệ:")
    parts.append(", ".join(TRAINING_DAY_ENUM))
    parts.append("")

    parts.append("Yêu cầu output JSON phải có đủ các field:")
    parts.append("- goal_style: 1 giá trị thuộc enum")
    parts.append("- priority_targets: list string (ví dụ abs, hips, upper chest, v taper)")
    parts.append("- priority_muscles: list muscle thuộc taxonomy")
    parts.append(f"- training_days: list đúng {days} phần tử, unique, thuộc mon..sun")
    parts.append(f"- weekly_focus_by_day: list đúng {days} phần tử, mỗi phần tử là object {{training_day, focus}}")
    parts.append("  - focus: list các object {muscle, rank} (rank 1 là ưu tiên cao nhất)")
    parts.append("- risk_notes: list string (cảnh báo logic)")
    parts.append("")

    parts.append("Hard constraints (bắt buộc):")
    parts.append("1) 1 training_day chỉ có đúng 1 rank=1 trong focus.")
    parts.append("2) Nếu 1 buổi có trên 2 nhóm cơ lớn thì nhóm cơ lớn không được rank 1 (tối thiểu rank 2).")
    parts.append("3) Hai training_day liền nhau không được trùng nhóm cơ lớn.")
    parts.append("4) Giới hạn số nhóm cơ/buổi theo days_per_week:")
    parts.append("   - 1: full body")
    parts.append("   - 2: tối đa 5 nhóm cơ/buổi")
    parts.append("   - 3: tối đa 4 nhóm cơ/buổi")
    parts.append("   - 4: tối đa 3 nhóm cơ/buổi")
    parts.append("   - 5-6: tối đa 2 nhóm cơ/buổi")
    parts.append("   - 7: tối đa 2 nhóm cơ/buổi")
    parts.append("5) Nếu experience != advanced: 1 nhóm cơ lớn không được xuất hiện >= 3 lần/tuần.")
    parts.append("6) Không dùng 'glutes'. Nếu nghĩ đến glutes thì phải dùng 'hips'.")
    parts.append("")

    parts.append("Checklist self-check trước khi trả JSON (nếu fail phải tự sửa):")
    parts.append("- training_days unique, đủ số phần tử")
    parts.append("- weekly_focus_by_day.training_day unique, khớp tập ngày với training_days")
    parts.append("- mỗi ngày đúng 1 rank=1")
    parts.append("- không trùng muscle trong cùng ngày")
    parts.append("- không trùng rank trong cùng ngày")
    parts.append("")
    parts.append("Gợi ý phân bổ:")
    parts.append("- Ưu tiên mục tiêu chính ở rank 1, mục tiêu phụ rank 2-3")
    parts.append("- Mỗi ngày nên có 2-4 nhóm cơ tùy thời lượng buổi")
    parts.append(f"- session_minutes hiện tại: {minutes}")
    parts.append("")
    parts.append("Chỉ trả về JSON hợp lệ, không thêm giải thích.")
    return "\n".join(parts)


def _canonicalize_internal_goal_dict(g: Dict[str, Any]) -> Dict[str, Any]:
    """Defensive canonicalize để tránh LLM lỡ dùng 'glutes'."""
    def canon_m(x: str) -> str:
        s = (x or "").strip().lower()
        return "hips" if s == "glutes" else s

    out = dict(g or {})

    # priority_muscles
    pm = out.get("priority_muscles")
    if isinstance(pm, list):
        out["priority_muscles"] = [canon_m(str(x)) for x in pm]

    # training_days
    td = out.get("training_days")
    if isinstance(td, list):
        out["training_days"] = [str(x).strip().lower() for x in td]

    # weekly_focus_by_day new shape
    w = out.get("weekly_focus_by_day")
    if isinstance(w, list):
        w2 = []
        for day in w:
            if not isinstance(day, dict):
                continue
            focus = day.get("focus")
            if isinstance(focus, list):
                focus2 = []
                for item in focus:
                    if not isinstance(item, dict):
                        continue
                    m = canon_m(str(item.get("muscle") or ""))
                    focus2.append({**item, "muscle": m})
                w2.append({**day, "focus": focus2})
            else:
                w2.append(day)
        out["weekly_focus_by_day"] = w2

    return out


def parse_intent_internal_goal_with_llm(
    llm: LLMClient,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Gọi LLM để sinh Internal Goal structured theo schema IntentInternalGoal.
    Có cache theo prompt hash.
    """
    prompt = _build_intent_prompt(profile)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    cached = cache_get("intent_prompt", prompt_hash)
    if cached is not None:
        return cached

    try:
        out = llm.generate_structured(prompt=prompt, schema_model=IntentInternalGoal)
    except Exception as e:
        out = {
            "error_type": "intent_generation_failed",
            "message": "Không parse được internal_goal theo schema (generate_structured failed).",
            "exception": str(e),
        }
        cache_set("intent_prompt", prompt_hash, out, ttl_seconds=INTENT_CACHE_TTL)
        return out

    # Defensive canonicalize
    if isinstance(out, dict):
        out = _canonicalize_internal_goal_dict(out)

    # Validate tối thiểu (bao gồm check số ngày theo days_per_week)
    errors = validate_intent_internal_goal(out, days_per_week=int(profile.get("days_per_week", 0)))
    if errors:
        out = {
            "error_type": "intent_validation_failed",
            "message": "LLM trả về internal_goal không hợp lệ theo contract",
            "errors": errors,
            "raw": out,
        }

    cache_set("intent_prompt", prompt_hash, out, ttl_seconds=INTENT_CACHE_TTL)
    return out


def _build_prompt(
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    documents: Optional[List[Document]] = None,
    issues: Optional[List[Dict[str, Any]]] = None,
    prev_plan: Optional[Dict[str, Any]] = None,
) -> str:
    parts: List[str] = []

    parts.append("Nhiệm vụ: tạo lịch tập tuần dạng JSON đúng schema, chỉ được dùng exercise_id có trong danh sách.")
    parts.append("")
    parts.append("Input profile:")
    parts.append(json.dumps(profile, ensure_ascii=False))
    parts.append("")
    parts.append("Constraints:")
    parts.append(json.dumps(constraints, ensure_ascii=False))
    parts.append("")

    parts.append("Candidate exercises (chỉ được chọn id trong danh sách này):")
    if documents is not None:
        parts.append(_format_candidate_lines_from_docs(documents, max_items=45))
    else:
        parts.append(_format_candidate_lines_fallback(candidates))

    if prev_plan:
        parts.append("")
        parts.append("Bản nháp trước đó (để sửa):")
        parts.append(json.dumps(prev_plan, ensure_ascii=False))

    if issues:
        parts.append("")
        parts.append("Issues cần sửa (bắt buộc xử lý):")
        parts.append(json.dumps(issues, ensure_ascii=False))

    parts.append("")
    parts.append("Yêu cầu output:")
    parts.append("- Chỉ trả về JSON hợp lệ, không thêm chữ giải thích.")
    parts.append("- Không dùng id ngoài candidate list.")
    parts.append("- Mỗi buổi tối đa max_exercises_per_day bài.")
    # Calendar-aware labels
    td = profile.get("training_days")
    if isinstance(td, list) and td:
        parts.append(f"- BẮT BUỘC: days[i].day hoặc days[i].training_day phải đúng theo training_days (theo thứ tự): {td}.")
        parts.append("  - Dùng token mon..sun, không dùng tiếng Việt như Thứ 2.")
    parts.append("- (Khuyến nghị) mỗi exercise nên có primary_muscle thuộc taxonomy để dễ đánh giá.")
    if constraints.get("min_exercises_per_day"):
        parts.append("- Mỗi buổi tối thiểu min_exercises_per_day bài.")

    return "\n".join(parts)


def generate_plan_with_llm(
    llm: LLMClient,
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    issues: Optional[List[Dict[str, Any]]] = None,
    prev_plan: Optional[Dict[str, Any]] = None,
    documents: Optional[List[Document]] = None,
) -> Dict[str, Any]:
    guard_error = _guard_before_llm(
        profile=profile,
        constraints=constraints,
        candidates=candidates,
    )
    if guard_error is not None:
        return guard_error

    prompt = _build_prompt(
        profile=profile,
        constraints=constraints,
        candidates=candidates,
        documents=documents,
        issues=issues,
        prev_plan=prev_plan,
    )

    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    cached = cache_get("plan_prompt", prompt_hash)
    if cached is not None:
        return cached

    out = llm.generate_plan_json(prompt=prompt)
    cache_set("plan_prompt", prompt_hash, out, ttl_seconds=PLAN_CACHE_TTL)
    return out
