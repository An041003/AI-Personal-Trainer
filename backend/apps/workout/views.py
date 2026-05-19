from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Plan
from apps.profiles.models import UserProfile
from apps.profiles.services.completeness import require_complete_profile
from apps.workout.models import Exercise, WorkoutIntentAnalysis
from apps.workout.serializers import ExerciseSerializer
from apps.workout.services.intent import analyze_workout_intent
from apps.workout.services.planning import generate_workout_plan
from apps.workout.services.replacement import add_workout_exercise, replace_workout_exercise


def analyze_and_save_intent(user, data):
    require_complete_profile(user)
    goal_text = (data.get("goal_text") or "").strip()
    if not goal_text:
        raise ValidationError({"goal_text": ["Workout goal text is required."]})
    result = analyze_workout_intent({"goal_text": goal_text})
    UserProfile.objects.update_or_create(
        user=user,
        defaults={"focus_muscles": result["focus_muscles"]},
    )
    WorkoutIntentAnalysis.objects.create(
        user=user,
        goal_text=goal_text,
        focus_muscles=result["focus_muscles"],
    )
    return result


class ExerciseListView(APIView):
    def get(self, request):
        queryset = Exercise.objects.all()
        q = request.query_params.get("q")
        muscles = request.query_params.get("muscles")
        show_all = str(request.query_params.get("all") or "").lower() in {"1", "true", "yes"}
        limit_param = request.query_params.get("limit")
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(body_part_raw__icontains=q))
        if muscles:
            for muscle in [item.strip() for item in muscles.split(",") if item.strip()]:
                queryset = queryset.filter(muscle_groups__contains=[muscle])
        queryset = queryset.order_by("title")
        if show_all or limit_param == "all":
            return Response(ExerciseSerializer(queryset, many=True).data)
        try:
            limit = min(max(int(limit_param or 100), 1), 500)
        except (TypeError, ValueError):
            limit = 100
        return Response(ExerciseSerializer(queryset[:limit], many=True).data)


class WorkoutIntentAnalyzeView(APIView):
    def post(self, request):
        return Response(analyze_and_save_intent(request.user, request.data))


class WorkoutPlanGenerateView(APIView):
    def post(self, request):
        require_complete_profile(request.user)
        return Response(generate_workout_plan(request.user, request.data))


class WorkoutPlanReplaceExerciseView(APIView):
    def post(self, request):
        require_complete_profile(request.user)
        try:
            return Response(replace_workout_exercise(request.user, request.data))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class WorkoutPlanAddExerciseView(APIView):
    def post(self, request):
        require_complete_profile(request.user)
        try:
            return Response(add_workout_exercise(request.user, request.data))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class WorkoutPlanLatestView(APIView):
    def get(self, request):
        plan = Plan.objects.filter(user=request.user, plan_type=Plan.PLAN_WORKOUT).first()
        if not plan:
            return Response(status=status.HTTP_204_NO_CONTENT)
        payload = plan.payload or {}
        if "plan" not in payload:
            payload = {"plan": payload, "warnings": [], "issues": []}
        return Response(payload)


class WorkoutGenerateFromGoalView(APIView):
    def post(self, request):
        internal_goal = analyze_and_save_intent(request.user, request.data)
        payload = {
            "profile": request.data.get("profile") or {},
            "internal_goal": internal_goal,
            "constraints": request.data.get("constraints") or {},
            "days_per_week": request.data.get("days_per_week"),
            "session_minutes": request.data.get("session_minutes"),
            "training_days": request.data.get("training_days"),
        }
        return Response(generate_workout_plan(request.user, payload))
