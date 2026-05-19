from django.db import models


class NutritionAtom(models.Model):
    canonical_name = models.CharField(max_length=120, unique=True)
    display_name_vi = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    food_role = models.CharField(max_length=100)
    edible_form = models.CharField(max_length=100, blank=True)
    kcal_per_100g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    protein_g_per_100g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carb_g_per_100g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fat_g_per_100g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fiber_g_per_100g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sodium_mg_per_100g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    default_serving_g = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    aliases = models.TextField(blank=True)
    source = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nutrition_atom"
        ordering = ["canonical_name"]

    def __str__(self):
        return self.display_name_vi or self.canonical_name

