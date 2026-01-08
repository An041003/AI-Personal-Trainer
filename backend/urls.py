from django.urls import path
from .views import ExerciseListView, ExerciseSearchView, WorkoutPlanGenerateAgentView

urlpatterns = [
    path("exercises/", ExerciseListView.as_view(), name="exercise-list"),
    path("exercises/search/", ExerciseSearchView.as_view(), name="exercise-search"),
    path("plan/generate-agent/", WorkoutPlanGenerateAgentView.as_view(), name="workout-plan-generate-agent"),

]
