from django.db import models
from pgvector.django import VectorField, HnswIndex

class Exercise(models.Model):
    title = models.CharField(max_length=255)
    body_part_raw = models.CharField(max_length=255, blank=True, default="")
    muscle_groups = models.JSONField(default=list, blank=True)

    image_url = models.URLField(blank=True, null=True)
    image_file = models.CharField(max_length=512, blank=True, default="")

    # Embedding fields
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    embedding_text = models.TextField(blank=True, default="")
    embedding_model = models.CharField(
        max_length=64,
        blank=True,
        default="text-embedding-3-small@1536",
    )


    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="wk_ex_emb_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self) -> str:
        return self.title

class NutritionAtom(models.Model):
    class Category(models.TextChoices):
        PROTEIN_ANIMAL = "protein_animal", "Protein Animal"
        VEGETABLE = "vegetable", "Vegetable"
        STARCHY_CARB = "starchy_carb", "Starchy Carb"
        FRUIT = "fruit", "Fruit"
        PROTEIN_PLANT = "protein_plant", "Protein Plant"
        DAIRY = "dairy", "Dairy"
        GRAIN = "grain", "Grain"
        FAT_OIL = "fat_oil", "Fat Oil"
        CONDIMENT = "condiment", "Condiment"
        BEVERAGE = "beverage", "Beverage"
        SUPPLEMENT = "supplement", "Supplement"

    class EdibleForm(models.TextChoices):
        RAW = "raw", "Raw"
        COOKED = "cooked", "Cooked"
        LIQUID = "liquid", "Liquid"
        POWDER = "powder", "Powder"

    canonical_name = models.CharField(max_length=128, unique=True, db_index=True)
    display_name_vi = models.CharField(max_length=255)

    category = models.CharField(max_length=32, choices=Category.choices)
    edible_form = models.CharField(max_length=16, choices=EdibleForm.choices)

    kcal_per_100g = models.DecimalField(max_digits=7, decimal_places=2)
    protein_g_per_100g = models.DecimalField(max_digits=7, decimal_places=2)
    carb_g_per_100g = models.DecimalField(max_digits=7, decimal_places=2)
    fat_g_per_100g = models.DecimalField(max_digits=7, decimal_places=2)

    fiber_g_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    sodium_mg_per_100g = models.IntegerField(default=0)

    default_serving_g = models.DecimalField(max_digits=7, decimal_places=2, default=100)
    aliases = models.TextField(blank=True, default="")

    source = models.CharField(max_length=32, default="manual_seed")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.canonical_name} ({self.display_name_vi})"