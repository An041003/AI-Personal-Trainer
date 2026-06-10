from datetime import date, datetime, time, timedelta, timezone as datetime_timezone

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Plan
from apps.common.services.daily_completion import completion_summary
from apps.nutrition.models import NutritionAtom
from apps.nutrition.models import NutritionCompletion
from apps.nutrition.serializers import NutritionAtomSerializer
from apps.nutrition.services.images import enrich_nutrition_payload
from apps.nutrition.services.planning import (
    generate_nutrition_plan,
    remember_stale_nutrition_plan,
    replace_nutrition_plan,
)
from apps.nutrition.services.rulebase import build_rulebase
from apps.profiles.serializers import UserProfileSerializer
from apps.profiles.services.completeness import require_complete_profile
from apps.profiles.services.metrics import calculate_metrics
from apps.profiles.views import ensure_profile_bundle


NUTRITION_PLAN_TIME_ZONE = datetime_timezone(timedelta(hours=7), "Asia/Saigon")


def _local_date(value=None):
    return timezone.localtime(value or timezone.now(), NUTRITION_PLAN_TIME_ZONE).date()


def _read_number(source, keys):
    if not isinstance(source, dict):
        return None
    for key in keys:
        value = source.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _month_bounds(month_value):
    today = _local_date(timezone.now())
    if month_value:
        try:
            year, month = [int(part) for part in month_value.split("-", 1)]
            start = date(year, month, 1)
        except (TypeError, ValueError):
            start = today.replace(day=1)
    else:
        start = today.replace(day=1)
    next_month = date(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
    start_dt = datetime.combine(start, time.min, tzinfo=NUTRITION_PLAN_TIME_ZONE)
    end_dt = datetime.combine(next_month, time.min, tzinfo=NUTRITION_PLAN_TIME_ZONE)
    return start, next_month, start_dt.astimezone(datetime_timezone.utc), end_dt.astimezone(datetime_timezone.utc)


def _daily_calorie_target(payload):
    derived = payload.get("derived_targets") or {}
    targets = payload.get("targets") or payload.get("daily_targets") or {}
    return (
        _read_number(derived, ["calorie_target_kcal", "calories", "calorie_target"])
        or _read_number(targets, ["calorie_target_kcal", "calories", "calorie_target"])
    )


class NutritionMetricsView(APIView):
    def post(self, request):
        if request.data:
            data = request.data
        else:
            profile, _ = ensure_profile_bundle(request.user)
            data = UserProfileSerializer(profile).data
        return Response(calculate_metrics(data))


class RulebasePreviewView(APIView):
    def post(self, request):
        require_complete_profile(request.user)
        return Response(build_rulebase(request.data))


class NutritionPlanGenerateView(APIView):
    def post(self, request):
        require_complete_profile(request.user)
        return Response(generate_nutrition_plan(request.user, request.data))


class NutritionPlanReplaceView(APIView):
    def post(self, request):
        require_complete_profile(request.user)
        try:
            return Response(replace_nutrition_plan(request.user, request.data))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class NutritionCompleteTodayView(APIView):
    def post(self, request):
        plan = Plan.objects.filter(user=request.user, plan_type=Plan.PLAN_NUTRITION).first()
        if not plan:
            return Response({"detail": "Generate today's meal plan before marking meals complete."}, status=status.HTTP_400_BAD_REQUEST)
        if _local_date(plan.created_at) != _local_date(timezone.now()):
            return Response({"detail": "Generate today's meal plan before marking meals complete."}, status=status.HTTP_400_BAD_REQUEST)
        NutritionCompletion.objects.update_or_create(
            user=request.user,
            nutrition_date=_local_date(),
            defaults={"plan": plan},
        )
        return Response(completion_summary(request.user))


class NutritionPlanLatestView(APIView):
    def get(self, request):
        plan = Plan.objects.filter(user=request.user, plan_type=Plan.PLAN_NUTRITION).first()
        if not plan:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if _local_date(plan.created_at) != _local_date(timezone.now()):
            remember_stale_nutrition_plan(
                request.user,
                plan.payload or {},
                source_plan_id=plan.id,
                source_created_at=plan.created_at,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        payload = plan.payload or {}
        enriched_payload = enrich_nutrition_payload(payload)
        if enriched_payload != payload:
            payload = enriched_payload
            plan.payload = enriched_payload
            plan.save(update_fields=["payload"])
        payload.setdefault("warnings", [])
        payload.setdefault("issues", [])
        payload.setdefault("shopping_list", [])
        return Response(payload)


class NutritionMonthlyCaloriesView(APIView):
    def get(self, request):
        month_start, next_month, start_dt, end_dt = _month_bounds(request.query_params.get("month"))
        plans = Plan.objects.filter(
            user=request.user,
            plan_type=Plan.PLAN_NUTRITION,
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        ).order_by("created_at")

        by_day = {}
        latest_target = None
        for plan in plans:
            payload = plan.payload or {}
            kcal = _read_number(payload.get("totals") or {}, ["kcal", "calories", "total_kcal"])
            target = _daily_calorie_target(payload)
            if target:
                latest_target = target
            local_day = _local_date(plan.created_at)
            entry = by_day.setdefault(local_day, {"date": local_day.isoformat(), "kcal": 0.0, "plan_count": 0})
            entry["kcal"] = kcal or 0.0
            entry["plan_count"] += 1

        series = []
        cursor = month_start
        while cursor < next_month:
            entry = by_day.get(cursor, {"date": cursor.isoformat(), "kcal": 0.0, "plan_count": 0})
            entry["kcal"] = round(entry["kcal"], 2)
            series.append(entry)
            cursor += timedelta(days=1)

        total_kcal = round(sum(item["kcal"] for item in series), 2)
        days_with_data = sum(1 for item in series if item["plan_count"])
        month_target = round((latest_target or 0) * len(series), 2) if latest_target else None
        return Response(
            {
                "month": month_start.strftime("%Y-%m"),
                "total_kcal": total_kcal,
                "daily_target_kcal": latest_target,
                "month_target_kcal": month_target,
                "days_with_data": days_with_data,
                "series": series,
            }
        )


class NutritionAtomListView(APIView):
    def get(self, request):
        queryset = NutritionAtom.objects.filter(is_active=True)
        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(
                Q(canonical_name__icontains=q) | Q(display_name_vi__icontains=q) | Q(aliases__icontains=q)
            )
        return Response(NutritionAtomSerializer(queryset[:100], many=True).data)
