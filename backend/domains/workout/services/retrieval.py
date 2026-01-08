from __future__ import annotations

from typing import Any, Dict, List
from langchain_core.documents import Document
from django.db import connection

from backend.services.retriever import retrieve_exercises
from backend.services.rerank_service import get_rerank_service
from backend.shared.simple_cache import cache_get, cache_set
from backend.domains.workout.contract import MUSCLE_TAXONOMY, is_valid_muscle


DEFAULT_K = 55  # Giới hạn retriever: top_k = 50-60
RETRIEVAL_CACHE_TTL = 900  # 15 phút
USE_RERANK = True  # Bật/tắt rerank
RERANK_TOP_N = 30  # Số lượng candidates sau rerank


def _distance_to_score(distance: Any) -> float:
    """
    CosineDistance càng nhỏ càng tốt. Convert thành score (càng lớn càng tốt).
    """
    try:
        d = float(distance)
        if d < 0:
            d = 0.0
        return 1.0 / (1.0 + d)  # d=0 => 1.0, d=1 => 0.5, d=2 => 0.33...
    except Exception:
        return 0.8


def build_candidate_pack(profile: Dict[str, Any], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal_text = (profile.get("goal_text") or "").strip().lower()
    internal_goal = profile.get("internal_goal") or {}
    goal_style = (internal_goal.get("goal_style") or "").strip().lower()

    raw_priority = internal_goal.get("priority_muscles") or profile.get("priority_muscles") or []
    # sanitize theo taxonomy
    base_muscles = []
    for m in raw_priority:
        m2 = (m or "").strip().lower()
        if is_valid_muscle(m2):
            base_muscles.append(m2)

    # fallback: nếu LLM chưa có priority_muscles thì dùng taxonomy mặc định
    if not base_muscles:
        base_muscles = list(MUSCLE_TAXONOMY)

    # query hint: ưu tiên goal_style, fallback goal_text
    query_base = goal_style or goal_text or "general_fitness"


    per_muscle = max(10, DEFAULT_K // max(1, len(base_muscles)))
    candidates: List[Dict[str, Any]] = []
    seen: set[int] = set()

    # Cache retrieval theo profile để tránh tốn chi phí khi user spam cùng input
    cache_key = (
        "retrieval_v1",
        profile.get("user_id") or "anon",
        goal_style,
        goal_text,
        profile.get("days_per_week"),
        profile.get("session_minutes"),
        tuple(sorted(base_muscles)),
        profile.get("seed"),
    )

    cached = cache_get("retrieval_candidates", cache_key)
    if cached is not None:
        return cached

    # Semantic chỉ hữu ích khi Postgres + pgvector + có embedding
    use_semantic = (connection.vendor == "postgresql")

    for m in base_muscles:
        m = (m or "").strip().lower()
        if not m:
            continue

        semantic_q = f"{query_base} exercise for {m}"

        # 1) Thử semantic (Postgres) hoặc q-based (fallback) trước
        objs = retrieve_exercises(
            q=semantic_q if use_semantic else "",
            muscles=[m],
            limit=per_muscle,
            use_semantic=use_semantic,
        )

        # 2) Nếu quá ít (hoặc SQLite), fallback sang muscle-only để chắc chắn có pool
        if len(objs) < max(3, per_muscle // 3):
            more = retrieve_exercises(
                q=None,
                muscles=[m],
                limit=per_muscle,
                use_semantic=False,
            )
            # nối thêm nhưng vẫn unique theo id
            if more:
                # giữ ưu tiên objs trước
                ids_in_objs = {x.id for x in objs}
                for x in more:
                    if x.id not in ids_in_objs:
                        objs.append(x)
                    if len(objs) >= per_muscle:
                        break

        for ex in objs:
            if ex.id in seen:
                continue
            seen.add(ex.id)

            dist = getattr(ex, "distance", None)
            score = _distance_to_score(dist) if dist is not None else 0.9

            candidates.append(
                {
                    "id": ex.id,
                    "title": ex.title,
                    "muscle_groups": ex.muscle_groups or [],
                    "image_url": ex.image_url,
                    "image_file": ex.image_file,
                    "score": float(score),
                    "reason": f"{'semantic' if (use_semantic and dist is not None) else 'muscle'}:{m}",
                }
            )

    # Global fallback nếu pool quá nhỏ
    if len(candidates) < 30:
        objs = retrieve_exercises(
            q=f"{query_base} workout exercise" if use_semantic else None,

            muscles=[],
            limit=50,
            use_semantic=use_semantic,
        )

        # Nếu vẫn ít, fallback sang lấy theo id (hoặc keyword rộng)
        if len(objs) < 10:
            objs = retrieve_exercises(q=None, muscles=[], limit=50, use_semantic=False)

        for ex in objs:
            if ex.id in seen:
                continue
            seen.add(ex.id)

            dist = getattr(ex, "distance", None)
            score = _distance_to_score(dist) if dist is not None else 0.5

            candidates.append(
                {
                    "id": ex.id,
                    "title": ex.title,
                    "muscle_groups": ex.muscle_groups or [],
                    "image_url": ex.image_url,
                    "image_file": ex.image_file,
                    "score": float(score),
                    "reason": "semantic_fallback_pool" if (use_semantic and dist is not None) else "fallback_pool",
                }
            )

    # Rerank candidates để cải thiện chất lượng
    if USE_RERANK and len(candidates) > 5:
        try:
            # Tạo query từ profile để rerank
            query_parts = [goal_style or goal_text or "workout"]
            if base_muscles:
                query_parts.extend(base_muscles[:3])  # Thêm top 3 priority muscles
            rerank_query = " ".join([x for x in query_parts if x])


            rerank_service = get_rerank_service()
            candidates = rerank_service.rerank(
                query=rerank_query,
                candidates=candidates,
                top_n=RERANK_TOP_N,
            )
            print(f"[RETRIEVAL] Rerank applied: query='{rerank_query}', top_n={RERANK_TOP_N}")
        except Exception as e:
            print(f"[RETRIEVAL] Rerank error: {e}, using original candidates")
            # Fallback: sort theo score nếu rerank fail
            candidates = sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)

    out = candidates[:DEFAULT_K]
    cache_set("retrieval_candidates", cache_key, out, ttl_seconds=RETRIEVAL_CACHE_TTL)
    return out


def candidate_pack_to_documents(candidates: List[Dict[str, Any]]) -> List[Document]:
    """Convert candidate pack to LangChain Documents"""
    docs: List[Document] = []
    for c in candidates:
        title = c.get("title", "")
        muscles = c.get("muscle_groups") or []
        equipment = c.get("equipment") or []
        level = c.get("level") or ""

        # page_content nên ngắn gọn để giảm token
        text = f"{title}\nMuscles: {', '.join(map(str, muscles))}\nEquipment: {', '.join(map(str, equipment))}\nLevel: {level}".strip()

        meta = {
            "id": c.get("id"),
            "title": title,
            "muscle_groups": muscles,
            "equipment": equipment,
            "level": level,
        }

        docs.append(Document(page_content=text, metadata=meta))
    return docs


