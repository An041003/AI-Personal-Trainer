from django.urls import path

from .views import (
    ExerciseListView,
    WorkoutGenerateFromGoalView,
    WorkoutCompleteTodayView,
    WorkoutCompletionSummaryView,
    WorkoutIntentAnalyzeView,
    WorkoutPlanAddExerciseView,
    WorkoutPlanGenerateView,
    WorkoutPlanLatestView,
    WorkoutPlanReplaceExerciseView,
)


urlpatterns = [
    path("exercises/", ExerciseListView.as_view(), name="exercise-list"),
    path("exercises/search/", ExerciseListView.as_view(), name="exercise-search"),
    path("intent/analyze/", WorkoutIntentAnalyzeView.as_view(), name="workout-intent-analyze"),
    path("plan/generate/", WorkoutPlanGenerateView.as_view(), name="workout-plan-generate"),
    path("plan/replace-exercise/", WorkoutPlanReplaceExerciseView.as_view(), name="workout-plan-replace-exercise"),
    path("plan/add-exercise/", WorkoutPlanAddExerciseView.as_view(), name="workout-plan-add-exercise"),
    path("plan/latest/", WorkoutPlanLatestView.as_view(), name="workout-plan-latest"),
    path("completion/summary/", WorkoutCompletionSummaryView.as_view(), name="workout-completion-summary"),
    path("completion/today/", WorkoutCompleteTodayView.as_view(), name="workout-complete-today"),
    path("plan/generate-from-goal/", WorkoutGenerateFromGoalView.as_view(), name="workout-generate-from-goal"),
]
