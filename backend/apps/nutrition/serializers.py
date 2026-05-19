from rest_framework import serializers

from .models import NutritionAtom


class NutritionAtomSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionAtom
        fields = [
            "id",
            "canonical_name",
            "display_name_vi",
            "category",
            "food_role",
            "edible_form",
            "kcal_per_100g",
            "protein_g_per_100g",
            "carb_g_per_100g",
            "fat_g_per_100g",
            "fiber_g_per_100g",
            "sodium_mg_per_100g",
            "default_serving_g",
            "aliases",
            "source",
            "is_active",
        ]

