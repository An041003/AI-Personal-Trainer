from datetime import timedelta, timezone as datetime_timezone

from django.utils import timezone

from apps.common.models import Plan
from apps.nutrition.models import NutritionCompletion
from apps.workout.models import WorkoutCompletion


DAILY_COMPLETION_TIME_ZONE = datetime_timezone(timedelta(hours=7), "Asia/Saigon")
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def local_date(value=None):
    return timezone.localtime(value or timezone.now(), DAILY_COMPLETION_TIME_ZONE).date()


def week_start(day):
    return day - timedelta(days=day.weekday())


def _normalize_day_key(value):
    key = str(value or "").strip().lower()[:3]
    return key if key in DAY_KEYS else ""


def _latest_workout_training_days(user):
    plan = Plan.objects.filter(user=user, plan_type=Plan.PLAN_WORKOUT).first()
    if not plan:
        return set()
    payload = plan.payload or {}
    workout_plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else payload
    days = workout_plan.get("days") if isinstance(workout_plan, dict) else []
    return {
        day_key
        for day_key in (_normalize_day_key(day.get("day")) for day in days or [])
        if day_key
    }


def _date_day_key(day):
    return DAY_KEYS[day.weekday()]


def completion_summary(user):
    today = local_date()
    start = week_start(today)
    end = start + timedelta(days=6)
    training_days = _latest_workout_training_days(user)

    workout_dates = set(
        WorkoutCompletion.objects.filter(user=user, workout_date__lte=today)
        .order_by("-workout_date")
        .values_list("workout_date", flat=True)
    )
    nutrition_dates = set(
        NutritionCompletion.objects.filter(user=user, nutrition_date__lte=today)
        .order_by("-nutrition_date")
        .values_list("nutrition_date", flat=True)
    )

    def requires_workout(day):
        return _date_day_key(day) in training_days

    def day_complete(day):
        nutrition_done = day in nutrition_dates
        workout_done = day in workout_dates
        return nutrition_done and (workout_done or not requires_workout(day))

    streak = 0
    cursor = today
    while day_complete(cursor):
        streak += 1
        cursor -= timedelta(days=1)

    week_days = [start + timedelta(days=offset) for offset in range(7)]
    completed_week_days = [day for day in week_days if day <= today and day_complete(day)]
    workout_week_days = sorted(day for day in workout_dates if start <= day <= end)
    nutrition_week_days = sorted(day for day in nutrition_dates if start <= day <= end)

    return {
        "today": today.isoformat(),
        "today_completed": day_complete(today),
        "today_requires_workout": requires_workout(today),
        "today_workout_completed": today in workout_dates,
        "today_nutrition_completed": today in nutrition_dates,
        "streak_days": streak,
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "completed_days_this_week": len(completed_week_days),
        "completed_dates_this_week": [day.isoformat() for day in completed_week_days],
        "workout_completed_dates_this_week": [day.isoformat() for day in workout_week_days],
        "nutrition_completed_dates_this_week": [day.isoformat() for day in nutrition_week_days],
        "training_days": sorted(training_days, key=DAY_KEYS.index),
    }
