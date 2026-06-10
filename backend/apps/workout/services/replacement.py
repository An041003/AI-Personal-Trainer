import uuid
from copy import deepcopy
from random import choice

from django.db.models import Q

from apps.common.audit import record_audit
from apps.common.models import Plan, ShortTermMemoryEntry
from apps.common.security import assert_user_plan_reference
from apps.common.short_term_memory import load_short_term_memory, remember_short_term_memory
from apps.workout.models import Exercise
from apps.workout.services.formatting import enrich_plan


def _as_index(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unique_values(values):
    result = []
    seen = set()
    for value in values or []:
        if value in (None, ""):
            continue
        key = str(value).lower()
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def _get_day(plan, target):
    days = plan.get("days") or []
    if not days:
        raise ValueError("Current workout plan is missing days.")

    day_index = _as_index(target.get("day_index"), -1)
    if 0 <= day_index < len(days):
        return days[day_index], day_index

    target_day = str(target.get("day") or "").strip().lower()
    if target_day:
        for index, day in enumerate(days):
            if str(day.get("day") or "").strip().lower() == target_day:
                return day, index

    raise ValueError("Selected workout day was not found.")


def _get_exercise(day, target):
    exercises = day.get("exercises") or []
    if not exercises:
        raise ValueError("Selected workout day is missing exercises.")

    exercise_index = _as_index(target.get("exercise_index"), -1)
    if 0 <= exercise_index < len(exercises):
        return exercises[exercise_index], exercise_index

    target_id = _as_index(target.get("exercise_id"), 0)
    if target_id:
        for index, exercise in enumerate(exercises):
            if int(exercise.get("exercise_id") or 0) == target_id:
                return exercise, index

    raise ValueError("Selected exercise was not found.")


def _exercise_payload(exercise, old_item):
    return {
        "exercise_id": exercise.id,
        "sets": old_item.get("sets") or 3,
        "reps": old_item.get("reps") or "8-12",
        "rest_sec": old_item.get("rest_sec") or 90,
        "notes": old_item.get("notes") or "Keep controlled form.",
        "title": exercise.title,
        "muscle_groups": exercise.muscle_groups,
        "equipment": exercise.equipment,
        "image_url": exercise.image_url,
        "image_file": exercise.image_file,
    }


def _session_memory(replace_request, old_item):
    session = replace_request.get("session_short_term_memory") or {}
    reason_code = (
        replace_request.get("reason_code")
        or replace_request.get("reason_type")
        or session.get("last_replace_reason")
        or "unknown"
    )
    avoid_ids = _unique_values(
        (replace_request.get("avoid_exercise_ids") or [])
        + (replace_request.get("old_exercise_ids") or [])
        + (session.get("avoid_exercise_ids") or [])
        + [old_item.get("exercise_id")]
    )
    avoid_titles = _unique_values(
        (replace_request.get("avoid_exercise_titles") or [])
        + (replace_request.get("old_exercise_titles") or [])
        + (session.get("avoid_exercise_titles") or [])
        + [old_item.get("title")]
    )
    return {
        "scope": "replace_exercise",
        "domain": "workout",
        "avoid_exercise_ids": [int(item) for item in avoid_ids if str(item).isdigit()],
        "avoid_exercise_titles": avoid_titles,
        "reason_code": reason_code,
        "must_match_muscle_group": True,
        "expires_policy": "current_session",
        "created_from_action": "replace_exercise",
    }


def _merge_workout_session_memory(replace_request, db_memory):
    updated = deepcopy(replace_request or {})
    session = deepcopy(updated.get("session_short_term_memory") or {})
    session["avoid_exercise_ids"] = _unique_values(
        (db_memory.get("avoid_exercise_ids") or [])
        + (session.get("avoid_exercise_ids") or [])
    )
    session["avoid_exercise_titles"] = _unique_values(
        (db_memory.get("avoid_exercise_titles") or [])
        + (session.get("avoid_exercise_titles") or [])
    )
    session["last_replace_reason"] = (
        session.get("last_replace_reason")
        or db_memory.get("last_replace_reason")
        or ""
    )
    updated["session_short_term_memory"] = session
    return updated


def _remember_workout_memory(user, memory, *, request_id, target):
    entities = []
    for exercise_id in memory.get("avoid_exercise_ids") or []:
        entities.append({"entity_type": "exercise_id", "entity_key": exercise_id, "raw_label": str(exercise_id)})
    for title in memory.get("avoid_exercise_titles") or []:
        entities.append({"entity_type": "exercise_title", "entity_key": title, "raw_label": title})
    if not entities:
        return []
    return remember_short_term_memory(
        user,
        domain=ShortTermMemoryEntry.DOMAIN_WORKOUT,
        scope=memory.get("scope") or "replace_exercise",
        entities=entities,
        reason_code=memory.get("reason_code") or "unknown",
        source_action=memory.get("created_from_action") or "replace_exercise",
        metadata={"request_id": str(request_id), "target": target},
    )


def _contains_any_json(field, values):
    query = Q()
    for value in values or []:
        query |= Q(**{f"{field}__contains": [value]})
    return query


def _plan_exercise_ids(plan):
    return [
        item.get("exercise_id")
        for day in plan.get("days", [])
        for item in day.get("exercises", [])
        if item.get("exercise_id")
    ]


def _random_exercise(queryset):
    ids = list(queryset.values_list("id", flat=True))
    if not ids:
        return None
    return Exercise.objects.filter(id=choice(ids)).first()


def _choose_same_muscle_exercise(current_plan, old_item, memory):
    old_muscles = old_item.get("muscle_groups") or []
    avoid_ids = set(memory.get("avoid_exercise_ids") or [])
    used_ids = set(_plan_exercise_ids(current_plan))
    blocked_ids = avoid_ids | used_ids

    queryset = Exercise.objects.exclude(id__in=blocked_ids)
    muscle_query = _contains_any_json("muscle_groups", old_muscles)
    if old_muscles and muscle_query:
        same_muscle = queryset.filter(muscle_query)
        if same_muscle.exists():
            return _random_exercise(same_muscle), []

    old_body_part = old_item.get("body_part_raw")
    if old_body_part:
        same_body_part = queryset.filter(body_part_raw__iexact=old_body_part)
        if same_body_part.exists():
            return _random_exercise(same_body_part), ["No same-muscle exercise found; used same body part."]

    fallback = _random_exercise(Exercise.objects.exclude(id__in=avoid_ids))
    warnings = ["No same-muscle exercise found; used the nearest available database exercise."] if fallback else []
    return fallback, warnings


def _save_plan_response(user, request_id, updated_plan, response, audit_payload, step):
    saved_plan = Plan.objects.create(
        user=user,
        plan_type=Plan.PLAN_WORKOUT,
        title=updated_plan.get("split") or "Updated workout plan",
        payload=response,
    )
    record_audit(
        request_id=request_id,
        domain="workout",
        step=step,
        plan=saved_plan,
        payload=audit_payload,
    )


def replace_workout_exercise(user, payload):
    request_id = uuid.uuid4()
    source_plan = assert_user_plan_reference(user, Plan.PLAN_WORKOUT, payload)
    current_plan = deepcopy((source_plan.payload or {}).get("plan") or {})
    if not current_plan.get("days"):
        raise ValueError("current_plan is required for workout replacement.")

    target = payload.get("target") or {}
    replace_request = deepcopy(payload.get("replace_request") or payload.get("replacement_request") or {})
    replace_request = _merge_workout_session_memory(
        replace_request,
        load_short_term_memory(user, domain=ShortTermMemoryEntry.DOMAIN_WORKOUT),
    )
    day, _ = _get_day(current_plan, target)
    old_item, exercise_index = _get_exercise(day, target)
    memory = _session_memory(replace_request, old_item)
    warnings = []
    issues = []

    selected_exercise_id = _as_index(replace_request.get("selected_exercise_id"), 0)
    if selected_exercise_id:
        replacement = Exercise.objects.filter(id=selected_exercise_id).first()
        if not replacement:
            raise ValueError("Selected exercise was not found.")
        old_muscles = set(old_item.get("muscle_groups") or [])
        new_muscles = set(replacement.muscle_groups or [])
        if old_muscles and not old_muscles.intersection(new_muscles):
            warnings.append("Selected exercise does not share a muscle group with the old exercise.")
    else:
        replacement, candidate_warnings = _choose_same_muscle_exercise(current_plan, old_item, memory)
        warnings.extend(candidate_warnings)
        if not replacement:
            raise ValueError("No replacement exercise is available.")

    day["exercises"][exercise_index] = _exercise_payload(replacement, old_item)
    updated_plan = enrich_plan(current_plan)
    response = {
        "request_id": str(request_id),
        "plan": updated_plan,
        "warnings": _unique_values(warnings),
        "issues": issues,
        "replacement": {
            "scope": "exercise",
            "target": target,
            "old_exercise": {
                "exercise_id": old_item.get("exercise_id"),
                "title": old_item.get("title"),
                "muscle_groups": old_item.get("muscle_groups") or [],
            },
            "new_exercise": {
                "exercise_id": replacement.id,
                "title": replacement.title,
                "muscle_groups": replacement.muscle_groups or [],
            },
            "reason_code": memory.get("reason_code"),
            "manual_selection": bool(selected_exercise_id),
        },
        "short_term_memory_applied": {
            "avoid_exercise_ids": memory.get("avoid_exercise_ids"),
            "avoid_exercise_titles": memory.get("avoid_exercise_titles"),
            "reason_code": memory.get("reason_code"),
        },
    }

    _save_plan_response(
        user=user,
        request_id=request_id,
        updated_plan=updated_plan,
        response=response,
        step="exercise_replacement",
        audit_payload={
            "target": target,
            "reason_code": memory.get("reason_code"),
            "old_exercise_id": old_item.get("exercise_id"),
            "new_exercise_id": replacement.id,
            "manual_selection": bool(selected_exercise_id),
        },
    )
    _remember_workout_memory(user, memory, request_id=request_id, target=target)
    return response


def add_workout_exercise(user, payload):
    request_id = uuid.uuid4()
    source_plan = assert_user_plan_reference(user, Plan.PLAN_WORKOUT, payload)
    current_plan = deepcopy((source_plan.payload or {}).get("plan") or {})
    if not current_plan.get("days"):
        raise ValueError("current_plan is required for adding an exercise.")

    target = payload.get("target") or {}
    add_request = deepcopy(payload.get("add_request") or payload.get("replace_request") or {})
    day, _ = _get_day(current_plan, target)
    selected_exercise_id = _as_index(
        payload.get("exercise_id") or add_request.get("selected_exercise_id") or add_request.get("exercise_id"),
        0,
    )
    if not selected_exercise_id:
        raise ValueError("exercise_id is required.")

    exercise = Exercise.objects.filter(id=selected_exercise_id).first()
    if not exercise:
        raise ValueError("Selected exercise was not found.")

    base_item = {
        "sets": add_request.get("sets") or 3,
        "reps": add_request.get("reps") or "8-12",
        "rest_sec": add_request.get("rest_sec") or 90,
        "notes": add_request.get("notes") or "Keep controlled form.",
    }
    day.setdefault("exercises", []).append(_exercise_payload(exercise, base_item))
    updated_plan = enrich_plan(current_plan)
    response = {
        "request_id": str(request_id),
        "plan": updated_plan,
        "warnings": [],
        "issues": [],
        "library_action": {
            "scope": "add_exercise",
            "target": target,
            "exercise": {
                "exercise_id": exercise.id,
                "title": exercise.title,
                "muscle_groups": exercise.muscle_groups or [],
            },
        },
    }

    _save_plan_response(
        user=user,
        request_id=request_id,
        updated_plan=updated_plan,
        response=response,
        step="exercise_add_from_library",
        audit_payload={
            "target": target,
            "exercise_id": exercise.id,
        },
    )
    return response
