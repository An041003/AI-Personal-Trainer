from __future__ import annotations

from typing import Any, Dict, List

from django.db import connection

from workout.services.retriever import retrieve_exercises

DEFAULT_K = 80


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
    goal = (profile.get("goal") or "hypertrophy").strip().lower()
    focus = profile.get("focus_muscles", []) or []
    base_muscles = focus[:] if focus else ["chest", "back", "quadriceps", "hamstrings", "shoulders", "arms", "core"]

    per_muscle = max(10, DEFAULT_K // max(1, len(base_muscles)))
    candidates: List[Dict[str, Any]] = []
    seen: set[int] = set()

    # Semantic chỉ hữu ích khi Postgres + pgvector + có embedding
    use_semantic = (connection.vendor == "postgresql")

    for m in base_muscles:
        m = (m or "").strip().lower()
        if not m:
            continue

        semantic_q = f"{goal} exercise for {m}"

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
            q=f"{goal} workout exercise" if use_semantic else None,
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

    return candidates[:DEFAULT_K]
