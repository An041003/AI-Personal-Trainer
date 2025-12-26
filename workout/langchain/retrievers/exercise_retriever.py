from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from workout.services.retrieval_service import build_candidate_pack


@dataclass
class ExerciseRetriever:
    """
    Retriever wrapper cho retrieval ORM hiện tại.
    Trả về list Document(page_content + metadata) để downstream dùng thống nhất.
    """

    top_k: int = 80
    include_fields: Optional[List[str]] = None

    def invoke(self, profile: Dict[str, Any], constraints: Dict[str, Any]) -> List[Document]:
        candidates = build_candidate_pack(profile, constraints)
        if self.top_k:
            candidates = candidates[: self.top_k]

        docs: List[Document] = []
        for c in candidates:
            title = c.get("title", "")
            muscles = c.get("muscle_groups") or []
            equipment = c.get("equipment") or c.get("equipments") or []
            level = c.get("level") or c.get("difficulty") or ""

            # page_content nên ngắn gọn để giảm token
            text = f"{title}\nMuscles: {', '.join(map(str, muscles))}\nEquipment: {', '.join(map(str, equipment))}\nLevel: {level}".strip()

            meta = {
                "id": c.get("id"),
                "title": title,
                "muscle_groups": muscles,
                "equipment": equipment,
                "level": level,
            }

            # nếu bạn muốn giữ thêm metadata (vd: score, video_url) thì add vào đây
            if self.include_fields:
                for k in self.include_fields:
                    if k in c and k not in meta:
                        meta[k] = c[k]

            docs.append(Document(page_content=text, metadata=meta))
        return docs
