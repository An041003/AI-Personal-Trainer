from django.contrib import admin

from .models import NutritionAtom


@admin.register(NutritionAtom)
class NutritionAtomAdmin(admin.ModelAdmin):
    list_display = ("id", "canonical_name", "display_name_vi", "category", "food_role", "is_active")
    list_filter = ("category", "food_role", "is_active")
    search_fields = ("canonical_name", "display_name_vi", "aliases")

