from django.urls import path

from .views import (
    NutritionAtomListView,
    NutritionCompleteTodayView,
    NutritionMetricsView,
    NutritionPlanGenerateView,
    NutritionPlanLatestView,
    NutritionMonthlyCaloriesView,
    NutritionPlanReplaceView,
    RulebasePreviewView,
)


urlpatterns = [
    path("metrics/", NutritionMetricsView.as_view(), name="nutrition-metrics"),
    path("rulebase/preview/", RulebasePreviewView.as_view(), name="nutrition-rulebase-preview"),
    path("plan/generate/", NutritionPlanGenerateView.as_view(), name="nutrition-plan-generate"),
    path("plan/replace/", NutritionPlanReplaceView.as_view(), name="nutrition-plan-replace"),
    path("plan/latest/", NutritionPlanLatestView.as_view(), name="nutrition-plan-latest"),
    path("plan/monthly-calories/", NutritionMonthlyCaloriesView.as_view(), name="nutrition-monthly-calories"),
    path("completion/today/", NutritionCompleteTodayView.as_view(), name="nutrition-complete-today"),
    path("atoms/", NutritionAtomListView.as_view(), name="nutrition-atoms"),
    path("atoms/search/", NutritionAtomListView.as_view(), name="nutrition-atoms-search"),
]
