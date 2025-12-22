from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from .models import Exercise
from .serializers import ExerciseSerializer
from .services.retriever import retrieve_exercises

from workout.serializers_plan import WorkoutPlanGenerateSerializer
from workout.orchestration.orchestrator import run_workout_planning_pipeline


class ExerciseListView(generics.ListAPIView):
    queryset = Exercise.objects.all().order_by("id")
    serializer_class = ExerciseSerializer


class ExerciseSearchView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "")
        limit = request.query_params.get("limit", "20")

        # Hỗ trợ nhiều tên param để khỏi nhầm
        muscles_raw = (
            request.query_params.get("muscles")
            or request.query_params.get("muscle_group")
            or request.query_params.get("muscle_groups")
            or ""
        )

        muscles = []
        if muscles_raw:
            muscles = [x.strip() for x in muscles_raw.split(",") if x.strip()]

        results = retrieve_exercises(q=q, muscles=muscles, limit=limit)
        data = ExerciseSerializer(results, many=True).data

        return Response({
            "q": q,
            "muscles": muscles,
            "limit": int(limit) if str(limit).isdigit() else 20,
            "count": len(data),
            "results": data,
        })

class WorkoutPlanGenerateAgentView(APIView):
    def post(self, request):
        ser = WorkoutPlanGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        state = run_workout_planning_pipeline(ser.validated_data)

        return Response({
            "request_id": state.request_id,
            "plan": state.final_plan,
            "warnings": state.warnings,
            "issues": state.issues,
            "audit": state.audit,
        }, status=status.HTTP_200_OK)