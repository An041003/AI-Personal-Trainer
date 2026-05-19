from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from apps.common.models import ShortTermMemoryEntry
from apps.common.utils import normalize_text


SHORT_TERM_MEMORY_TTL_DAYS = 7


def _expires_at(ttl_days=SHORT_TERM_MEMORY_TTL_DAYS):
    return timezone.now() + timedelta(days=ttl_days)


def _entity_key(value):
    key = normalize_text(value)
    return key or str(value or "").strip().lower()


def purge_expired_short_term_memory(user=None):
    queryset = ShortTermMemoryEntry.objects.filter(expires_at__lte=timezone.now())
    if user is not None:
        queryset = queryset.filter(user=user)
    deleted_count, _ = queryset.delete()
    return deleted_count


def remember_short_term_memory(
    user,
    *,
    domain,
    scope,
    entities,
    reason_code="unknown",
    source_action="",
    metadata=None,
    ttl_days=SHORT_TERM_MEMORY_TTL_DAYS,
):
    purge_expired_short_term_memory(user=user)
    expires_at = _expires_at(ttl_days)
    saved = []

    for entity in entities or []:
        entity_type = str(entity.get("entity_type") or "").strip()
        raw_value = entity.get("entity_key")
        raw_label = str(entity.get("raw_label") or raw_value or "").strip()
        key = _entity_key(raw_value or raw_label)
        if not entity_type or not key:
            continue

        defaults = {
            "raw_label": raw_label[:255],
            "reason_code": reason_code or "unknown",
            "source_action": source_action or "",
            "expires_at": expires_at,
            "metadata": metadata or {},
        }
        entry, created = ShortTermMemoryEntry.objects.get_or_create(
            user=user,
            domain=domain,
            scope=scope,
            entity_type=entity_type,
            entity_key=key[:255],
            defaults=defaults,
        )
        if not created:
            ShortTermMemoryEntry.objects.filter(pk=entry.pk).update(
                raw_label=defaults["raw_label"],
                reason_code=defaults["reason_code"],
                source_action=defaults["source_action"],
                expires_at=defaults["expires_at"],
                metadata=defaults["metadata"],
                hit_count=F("hit_count") + 1,
            )
        saved.append(entry)
    return saved


def load_short_term_memory(user, *, domain, scopes=None):
    purge_expired_short_term_memory(user=user)
    queryset = ShortTermMemoryEntry.objects.filter(
        user=user,
        domain=domain,
        expires_at__gt=timezone.now(),
    ).order_by("-updated_at")
    if scopes:
        queryset = queryset.filter(scope__in=scopes)

    if domain == ShortTermMemoryEntry.DOMAIN_NUTRITION:
        memory = {
            "avoid_recipe_names": [],
            "avoid_ingredient_names": [],
            "avoid_atom_ids": [],
            "last_replace_reason": "",
        }
        for entry in queryset:
            value = entry.raw_label or entry.entity_key
            if entry.entity_type == "recipe":
                memory["avoid_recipe_names"].append(value)
            elif entry.entity_type == "ingredient":
                memory["avoid_ingredient_names"].append(value)
            elif entry.entity_type == "atom_id":
                try:
                    memory["avoid_atom_ids"].append(int(value))
                except (TypeError, ValueError):
                    continue
            if not memory["last_replace_reason"] and entry.reason_code:
                memory["last_replace_reason"] = entry.reason_code
        memory["avoid_recipe_names"] = _unique(memory["avoid_recipe_names"])
        memory["avoid_ingredient_names"] = _unique(memory["avoid_ingredient_names"])
        memory["avoid_atom_ids"] = _unique(memory["avoid_atom_ids"])
        return memory

    if domain == ShortTermMemoryEntry.DOMAIN_WORKOUT:
        memory = {
            "avoid_exercise_ids": [],
            "avoid_exercise_titles": [],
            "last_replace_reason": "",
        }
        for entry in queryset:
            value = entry.raw_label or entry.entity_key
            if entry.entity_type == "exercise_id":
                try:
                    memory["avoid_exercise_ids"].append(int(value))
                except (TypeError, ValueError):
                    continue
            elif entry.entity_type == "exercise_title":
                memory["avoid_exercise_titles"].append(value)
            if not memory["last_replace_reason"] and entry.reason_code:
                memory["last_replace_reason"] = entry.reason_code
        memory["avoid_exercise_ids"] = _unique(memory["avoid_exercise_ids"])
        memory["avoid_exercise_titles"] = _unique(memory["avoid_exercise_titles"])
        return memory

    return {}


def _unique(values):
    result = []
    seen = set()
    for value in values or []:
        if value in (None, ""):
            continue
        key = str(value).strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result
