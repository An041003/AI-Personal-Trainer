from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set

from workout.llms.llm_client import LLMClient


def _response_schema() -> Dict[str, Any]:
    # Schema tối thiểu để ép JSON đúng format
    return {
        "type": "OBJECT",
        "required": ["goal", "days_per_week", "session_minutes", "split", "days"],
        "properties": {
            "goal": {"type": "STRING"},
            "days_per_week": {"type": "INTEGER"},
            "session_minutes": {"type": "INTEGER"},
            "split": {"type": "STRING"},
            "days": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "required": ["day", "exercises"],
                    "properties": {
                        "day": {"type": "STRING"},
                        "exercises": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "required": ["exercise_id", "sets", "reps", "rest_sec", "notes"],
                                "properties": {
                                    "exercise_id": {"type": "INTEGER"},
                                    "sets": {"type": "INTEGER"},
                                    "reps": {"type": "STRING"},
                                    "rest_sec": {"type": "INTEGER"},
                                    "notes": {"type": "STRING"},
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def _build_prompt(
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    issues: Optional[List[Dict[str, Any]]] = None,
    prev_plan: Optional[Dict[str, Any]] = None,
) -> str:
    # Giữ prompt gọn: LLM chỉ cần candidate ids + vài fields để chọn hợp lý
    candidate_lines = []
    for c in candidates:
        mg = ",".join([str(x) for x in (c.get("muscle_groups") or [])])
        candidate_lines.append(f"- id={c['id']} | {c.get('title','')} | muscles={mg}")

    parts = []
    parts.append("Nhiệm vụ: tạo lịch tập tuần dạng JSON đúng schema, chỉ được dùng exercise_id có trong danh sách.")
    parts.append("")
    parts.append("Input profile:")
    parts.append(json.dumps(profile, ensure_ascii=False))
    parts.append("")
    parts.append("Constraints:")
    parts.append(json.dumps(constraints, ensure_ascii=False))
    parts.append("")
    parts.append("Candidate exercises (chỉ được chọn id trong danh sách này):")
    parts.append("\n".join(candidate_lines))

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
    return "\n".join(parts)


def generate_plan_with_llm(
    llm: LLMClient,
    profile: Dict[str, Any],
    constraints: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    issues: Optional[List[Dict[str, Any]]] = None,
    prev_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    prompt = _build_prompt(profile, constraints, candidates, issues=issues, prev_plan=prev_plan)
    return llm.generate_plan_json(prompt=prompt, response_schema=_response_schema())
