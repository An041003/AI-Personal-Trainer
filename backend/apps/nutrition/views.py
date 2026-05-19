from datetime import timedelta, timezone as datetime_timezone

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Plan
from apps.nutrition.models import NutritionAtom
from apps.nutrition.serializers import NutritionAtomSerializer
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


def _local_date(value):
    return timezone.localtime(value, NUTRITION_PLAN_TIME_ZONE).date()


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
        payload.setdefault("warnings", [])
        payload.setdefault("issues", [])
        payload.setdefault("shopping_list", [])
        return Response(payload)


class NutritionAtomListView(APIView):
    def get(self, request):
        queryset = NutritionAtom.objects.filter(is_active=True)
        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(
                Q(canonical_name__icontains=q) | Q(display_name_vi__icontains=q) | Q(aliases__icontains=q)
            )
        return Response(NutritionAtomSerializer(queryset[:100], many=True).data)
