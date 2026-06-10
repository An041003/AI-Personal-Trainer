from django.contrib import admin

from .models import NutritionAtom, NutritionCompletion


@admin.register(NutritionAtom)
class NutritionAtomAdmin(admin.ModelAdmin):
    list_display = ("id", "canonical_name", "display_name_vi", "category", "food_role", "is_active")
    list_filter = ("category", "food_role", "is_active")
    search_fields = ("canonical_name", "display_name_vi", "aliases")


@admin.register(NutritionCompletion)
class NutritionCompletionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "nutrition_date", "plan", "created_at")
    list_filter = ("nutrition_date", "created_at")
    search_fields = ("user__username", "user__email")
