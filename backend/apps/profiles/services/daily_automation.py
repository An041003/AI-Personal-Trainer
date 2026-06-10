from datetime import datetime, time, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.common.models import Plan
from apps.nutrition.services.planning import generate_nutrition_plan
from apps.nutrition.services.rulebase import build_rulebase
from apps.profiles.models import UserPreferences, UserProfile
from apps.profiles.services.completeness import profile_completeness
from apps.profiles.services.dashboard import dashboard_greeting
from apps.profiles.services.metrics import calculate_metrics
from apps.profiles.services.weather import update_profile_weather


DAILY_AUTOMATION_TIME_ZONE = datetime_timezone(timedelta(hours=7), "Asia/Saigon")


def _local_date(value=None):
    value = value or timezone.now()
    return timezone.localtime(value, DAILY_AUTOMATION_TIME_ZONE).date()


def _day_bounds(day):
    start = datetime.combine(day, time.min, tzinfo=DAILY_AUTOMATION_TIME_ZONE)
    end = start + timedelta(days=1)
    return start.astimezone(datetime_timezone.utc), end.astimezone(datetime_timezone.utc)


def _profile_payload(profile):
    age = None
    if profile.birth_year:
        age = max(_local_date().year - profile.birth_year, 0)
    return {
        "sex": profile.sex,
        "birth_year": profile.birth_year,
        "age": age,
        "height_cm": float(profile.height_cm) if profile.height_cm is not None else None,
        "weight_kg": float(profile.weight_kg) if profile.weight_kg is not None else None,
        "waist_cm": float(profile.waist_cm) if profile.waist_cm is not None else None,
        "neck_cm": float(profile.neck_cm) if profile.neck_cm is not None else None,
        "hip_cm": float(profile.hip_cm) if profile.hip_cm is not None else None,
        "activity_level": profile.activity_level,
        "experience_level": profile.experience_level,
        "goal_type": profile.goal_type,
        "country": profile.country,
        "city": profile.city,
        "latitude": float(profile.latitude) if profile.latitude is not None else None,
        "longitude": float(profile.longitude) if profile.longitude is not None else None,
    }


def _preferences_payload(preferences):
    return {
        "dietary_style": preferences.dietary_style,
        "allergies": preferences.allergies or [],
        "disliked_foods": preferences.disliked_foods or [],
        "favorite_foods": preferences.favorite_foods or [],
        "avoid_ingredients": preferences.avoid_ingredients or [],
        "medical_conditions": preferences.medical_conditions or [],
        "notes": preferences.notes,
    }


def _weather_payload(profile):
    if profile.location_source == "gps" and profile.latitude is not None and profile.longitude is not None:
        return {
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "city": profile.city,
            "country": profile.country,
        }
    if profile.city:
        return {"city": profile.city, "country": profile.country}
    return None


def _has_nutrition_plan_today(user, *, day=None):
    start, end = _day_bounds(day or _local_date())
    return Plan.objects.filter(
        user=user,
        plan_type=Plan.PLAN_NUTRITION,
        created_at__gte=start,
        created_at__lt=end,
    ).exists()


def _nutrition_payload(profile, preferences):
    profile_data = _profile_payload(profile)
    pref_data = _preferences_payload(preferences)
    metrics = profile.metrics_snapshot or calculate_metrics(profile_data)
    if not profile.metrics_snapshot:
        profile.metrics_snapshot = metrics
        profile.metrics_updated_at = timezone.now()
        profile.save(update_fields=["metrics_snapshot", "metrics_updated_at", "updated_at"])

    rulebase = build_rulebase(
        {
            "profile": profile_data,
            "metrics": metrics,
            "goal": {"goal_type": profile.goal_type, "goal_mode": "standard"},
            "preferences": pref_data,
            "medical": {"conditions": pref_data.get("medical_conditions") or []},
        }
    )
    return {
        "derived_targets": rulebase["derived_targets"],
        "constraints": rulebase["constraints"],
        "preferences": pref_data,
        "medical_flags": rulebase["medical_flags"],
        "extra_restrictions": [],
        "options": {"optimizer_iters": 200, "max_llm_retries": 1},
    }


def run_daily_automation(*, user_ids=None, force=False, skip_weather=False, skip_greeting=False, skip_nutrition=False):
    User = get_user_model()
    queryset = User.objects.filter(is_active=True).order_by("id")
    if user_ids:
        queryset = queryset.filter(id__in=user_ids)

    summary = {
        "users_seen": 0,
        "users_skipped_incomplete_profile": 0,
        "weather_refreshed": 0,
        "greetings_generated": 0,
        "nutrition_generated": 0,
        "nutrition_skipped_existing": 0,
        "errors": [],
    }

    for user in queryset:
        summary["users_seen"] += 1
        profile, _ = UserProfile.objects.get_or_create(user=user)
        preferences, _ = UserPreferences.objects.get_or_create(user=user)

        if not profile_completeness(profile)["is_complete"]:
            summary["users_skipped_incomplete_profile"] += 1
            continue

        weather_payload = _weather_payload(profile)
        if weather_payload and not skip_weather:
            try:
                update_profile_weather(profile, weather_payload)
                summary["weather_refreshed"] += 1
            except Exception as exc:
                summary["errors"].append({"user_id": user.id, "step": "weather", "error": str(exc)[:200]})

        if not skip_greeting:
            try:
                dashboard_greeting(profile, force=force)
                summary["greetings_generated"] += 1
            except Exception as exc:
                summary["errors"].append({"user_id": user.id, "step": "greeting", "error": str(exc)[:200]})

        if skip_nutrition:
            continue
        if not force and _has_nutrition_plan_today(user):
            summary["nutrition_skipped_existing"] += 1
            continue
        try:
            generate_nutrition_plan(user, _nutrition_payload(profile, preferences))
            summary["nutrition_generated"] += 1
        except Exception as exc:
            summary["errors"].append({"user_id": user.id, "step": "nutrition", "error": str(exc)[:200]})

    return summary
