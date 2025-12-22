from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Union
from django.db import connection
from pgvector.django import CosineDistance

from workout.models import Exercise
from workout.services.embedding_service import embed_query

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _clean_list(items: Iterable[str]) -> List[str]:
    out = []
    for x in items:
        x = (x or "").strip().lower()
        if x:
            out.append(x)
    # unique giữ thứ tự
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


def retrieve_exercises(
    q: Optional[str] = None,
    muscles: Optional[Sequence[str]] = None,
    limit: Union[int, str] = DEFAULT_LIMIT,
    use_semantic: bool = True,
) -> List[Exercise]:
    q = (q or "").strip()
    muscles = _clean_list(muscles or [])

    try:
        limit_int = int(limit)
    except Exception:
        limit_int = DEFAULT_LIMIT
    limit_int = max(1, min(limit_int, MAX_LIMIT))

    qs = Exercise.objects.all()

    # Semantic path (Postgres + có embedding + có query)
    if use_semantic and q and connection.vendor == "postgresql":
        qs2 = qs.exclude(embedding__isnull=True)

        if muscles:
            for m in muscles:
                qs2 = qs2.filter(muscle_groups__contains=[m])

        qvec = embed_query(q, output_dim=768)
        return list(
            qs2.annotate(distance=CosineDistance("embedding", qvec))
               .order_by("distance")[:limit_int]
        )

    # Fallback path (logic hiện tại)
    if q:
        qs = qs.filter(title__icontains=q)

    if muscles and connection.vendor == "sqlite":
        objs = list(qs.order_by("id"))
        wanted = set(muscles)
        filtered: List[Exercise] = []
        for ex in objs:
            mg = set(str(x).lower() for x in (ex.muscle_groups or []))
            if wanted.issubset(mg):
                filtered.append(ex)
        return filtered[:limit_int]

    if muscles:
        for m in muscles:
            qs = qs.filter(muscle_groups__contains=[m])

    return list(qs.order_by("id")[:limit_int])