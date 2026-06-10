import json
import uuid

from django.core.exceptions import ImproperlyConfigured

from apps.common.audit import record_audit
from apps.common.models import Plan
from apps.common.openai_client import (
    generate_json,
    get_token_usage,
    reset_token_usage_tracking,
    start_token_usage_tracking,
)
from apps.common.prompt import WORKOUT_PLAN_RULES, WORKOUT_PLAN_SYSTEM_PROMPT
from apps.profiles.models import UserProfile
from apps.workout.services.evaluation import evaluate_workout_plan
from apps.workout.services.formatting import enrich_plan
from apps.workout.services.retrieval import candidate_pack, retrieve_candidates

DEFAULT_TRAINING_DAYS = ["mon", "wed", "fri"]


def _fallback_plan(internal_goal, candidates, max_exercises_per_day):
    training_days = internal_goal.get("training_days") or DEFAULT_TRAINING_DAYS
    days = []
    cursor = 0
    candidate_list = list(candidates)
    for day in training_days:
        selected = []
        for _ in range(min(max_exercises_per_day, 5)):
            if not candidate_list:
                break
            exercise = candidate_list[cursor % len(candidate_list)]
            selected.append(
                {
                    "exercise_id": exercise.id,
                    "sets": 3,
                    "reps": "8-12",
                    "rest_sec": 90,
                    "notes": "Keep 1-2 reps in reserve.",
                }
            )
            cursor += 1
        days.append({"day": day, "title": "Training day", "exercises": selected})

    return {
        "goal": internal_goal.get("goal_style") or "mixed",
        "days_per_week": len(training_days),
        "session_minutes": internal_goal.get("session_minutes") or 60,
        "split": "fallback balanced split",
        "days": days,
    }


def _list_value(payload, key):
    value = payload.get(key)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value or []


def _int_value(payload, key, default):
    try:
        return int(payload.get(key) or default)
    except (TypeError, ValueError):
        return default


def _profile_experience_level(user):
    try:
        return user.profile.experience_level or "beginner"
    except (AttributeError, UserProfile.DoesNotExist):
        return "beginner"


def build_generation_goal(payload, *, experience_level="beginner"):
    internal_goal = dict(payload.get("internal_goal") or {})
    plan_settings = payload.get("plan_settings") or {}
    training_days = _list_value(payload, "training_days") or _list_value(plan_settings, "training_days")
    days_per_week = _int_value(payload, "days_per_week", _int_value(plan_settings, "days_per_week", len(training_days) or 3))
    if not training_days:
        training_days = DEFAULT_TRAINING_DAYS[: max(1, min(days_per_week, 7))]

    internal_goal.update(
        {
            "days_per_week": len(training_days),
            "session_minutes": _int_value(payload, "session_minutes", _int_value(plan_settings, "session_minutes", 60)),
            "training_days": training_days,
            "equipment": [],
            "experience_level": experience_level or "beginner",
        }
    )

    if internal_goal.get("focus_muscles") and "goal_text" in internal_goal:
        internal_goal.pop("goal_text", None)

    return internal_goal


def generate_workout_plan(user, payload):
    token = start_token_usage_tracking()
    try:
        return _generate_workout_plan(user, payload)
    finally:
        reset_token_usage_tracking(token)


def _generate_workout_plan(user, payload):
    request_id = uuid.uuid4()
    internal_goal = build_generation_goal(payload, experience_level=_profile_experience_level(user))
    if not internal_goal.get("focus_muscles"):
        try:
            internal_goal["focus_muscles"] = list(user.profile.focus_muscles or [])
        except (AttributeError, UserProfile.DoesNotExist):
            internal_goal["focus_muscles"] = []
    if not internal_goal.get("focus_muscles"):
        raise ValueError("focus_muscles is required. Analyze a workout goal or set focus muscles before generating a plan.")
    constraints = payload.get("constraints") or {}
    max_exercises = int(constraints.get("max_exercises_per_day") or 6)
    max_repairs = int(constraints.get("max_repair_iterations") or 2)

    candidates = retrieve_candidates(internal_goal, top_k=int(constraints.get("top_k") or 80))
    record_audit(
        request_id=request_id,
        domain="workout",
        step="retrieval",
        payload={"candidate_count": len(candidates), "internal_goal": internal_goal},
    )

    profile_context = dict(payload.get("profile") or {})
    profile_context["experience_level"] = internal_goal["experience_level"]

    prompt = {
        "profile": profile_context,
        "internal_goal": internal_goal,
        "constraints": {"max_exercises_per_day": max_exercises},
        "candidate_exercises": candidate_pack(candidates),
        "rules": WORKOUT_PLAN_RULES,
    }

    try:
        plan = generate_json(WORKOUT_PLAN_SYSTEM_PROMPT, json.dumps(prompt, ensure_ascii=True), max_retries=1)
    except ImproperlyConfigured:
        plan = _fallback_plan(internal_goal, candidates, max_exercises)
    except Exception as exc:
        record_audit(
            request_id=request_id,
            domain="workout",
            step="openai_error",
            payload={"error": str(exc)[:500]},
        )
        plan = _fallback_plan(internal_goal, candidates, max_exercises)

    candidate_ids = [item.id for item in candidates]
    evaluation = evaluate_workout_plan(
        plan,
        candidate_ids=candidate_ids,
        internal_goal=internal_goal,
        max_exercises_per_day=max_exercises,
    )

    repairs = 0
    while evaluation["issues"] and repairs < max_repairs:
        repairs += 1
        repair_prompt = {
            "previous_plan": plan,
            "issues": evaluation["issues"],
            "candidate_exercises": candidate_pack(candidates),
            "internal_goal": internal_goal,
        }
        try:
            plan = generate_json(WORKOUT_PLAN_SYSTEM_PROMPT, json.dumps(repair_prompt, ensure_ascii=True), max_retries=0)
            evaluation = evaluate_workout_plan(
                plan,
                candidate_ids=candidate_ids,
                internal_goal=internal_goal,
                max_exercises_per_day=max_exercises,
            )
        except Exception:
            break

    plan = enrich_plan(plan)
    response = {
        "request_id": str(request_id),
        "plan": plan,
        "warnings": evaluation["warnings"],
        "issues": evaluation["issues"],
    }
    saved_plan = Plan.objects.create(
        user=user,
        plan_type=Plan.PLAN_WORKOUT,
        title=plan.get("split") or "Workout plan",
        payload=response,
    )
    record_audit(
        request_id=request_id,
        domain="workout",
        step="final",
        plan=saved_plan,
        payload={
            "issues": evaluation["issues"],
            "warnings": evaluation["warnings"],
            "repairs": repairs,
            "token_usage": get_token_usage(),
        },
    )

    return response
