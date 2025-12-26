from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from workout.llms.llm_client import LLMClient


def _format_candidate_lines_from_docs(documents: List[Document], max_items: int = 60) -> str:
    lines: List[str] = []
    for d in documents[:max_items]:
        m = d.metadata or {}
        eid = m.get("id")
        title = m.get("title", "")
        muscles = m.get("muscle_groups") or []
        equipment = m.get("equipment") or []
        level = m.get("level") or ""
        lines.append(
            f"- id={eid} | {title} | muscles={','.join(map(str, muscles))} | "
            f"equip={','.join(map(str, equipment))} | level={level}"
        )
    return "\n".join(lines)


def _format_candidate_lines_fallback(candidates: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for c in candidates:
        mg = ",".join([str(x) for x in (c.get("muscle_groups") or [])])
        lines.append(f"- id={c['id']} | {c.get('title','')} | muscles={mg}")
    return "\n".join(lines)


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
        parts.append(_format_candidate_lines_from_docs(documents, max_items=60))
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
    documents: Optional[List[Document]] = None,  # Phase 3: thêm tham số này
) -> Dict[str, Any]:
    prompt = _build_prompt(
        profile=profile,
        constraints=constraints,
        candidates=candidates,
        documents=documents,
        issues=issues,
        prev_plan=prev_plan,
    )
    return llm.generate_plan_json(prompt=prompt)
