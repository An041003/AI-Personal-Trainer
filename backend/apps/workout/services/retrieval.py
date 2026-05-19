from django.db.models import Q

from apps.common.openai_client import embed_texts
from apps.workout.models import Exercise


def _json_contains_any(field, values):
    query = Q()
    for value in values or []:
        query |= Q(**{f"{field}__contains": [value]})
    return query


def retrieve_candidates(internal_goal, *, top_k=80):
    focus_muscles = internal_goal.get("focus_muscles") or []
    equipment = internal_goal.get("equipment") or []

    queryset = Exercise.objects.all()
    muscle_query = _json_contains_any("muscle_groups", focus_muscles)
    if muscle_query:
        muscle_filtered = queryset.filter(muscle_query)
        if muscle_filtered.exists():
            queryset = muscle_filtered

    equipment_query = _json_contains_any("equipment", equipment)
    if equipment and equipment_query:
        equipment_filtered = queryset.filter(equipment_query)
        if equipment_filtered.exists():
            queryset = equipment_filtered

    query_text = " ".join(
        [
            str(internal_goal.get("goal_style") or ""),
            " ".join(focus_muscles),
            " ".join(equipment),
            str(internal_goal.get("experience_level") or ""),
        ]
    ).strip()

    if query_text:
        try:
            from pgvector.django import CosineDistance

            embedding = embed_texts([query_text])[0]
            ranked = queryset.exclude(embedding=None).order_by(CosineDistance("embedding", embedding))
            if ranked.exists():
                return list(ranked[:top_k])
        except Exception:
            pass

    if not queryset.exists():
        queryset = Exercise.objects.all()
    return list(queryset[:top_k])


def candidate_pack(candidates):
    lines = []
    for item in candidates:
        lines.append(
            f"id={item.id} | title={item.title} | muscles={','.join(item.muscle_groups)} | "
            f"equipment={','.join(item.equipment)} | level={item.level}"
        )
    return "\n".join(lines)
