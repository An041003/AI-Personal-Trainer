from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Exercise(models.Model):
    title = models.CharField(max_length=255, unique=True)
    body_part_raw = models.CharField(max_length=100, blank=True)
    muscle_groups = models.JSONField(default=list, blank=True)
    equipment = models.JSONField(default=list, blank=True)
    level = models.CharField(max_length=30, default="beginner")
    image_url = models.URLField(blank=True)
    image_file = models.CharField(max_length=255, blank=True)
    embedding = VectorField(dimensions=settings.OPENAI_EMBED_DIM, null=True, blank=True)
    embedding_text = models.TextField(blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exercise"
        ordering = ["title"]
        indexes = [
            HnswIndex(
                name="wk_ex_emb_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return self.title


class WorkoutIntentAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_intent_analyses")
    goal_text = models.TextField(blank=True)
    focus_muscles = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workout_intent_analysis"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Intent analysis #{self.pk}"


class WorkoutCompletion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_completions")
    workout_date = models.DateField(db_index=True)
    plan = models.ForeignKey(
        "common.Plan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workout_completions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workout_completion"
        ordering = ["-workout_date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "workout_date"], name="uniq_workout_completion_user_date"),
        ]
        indexes = [
            models.Index(fields=["user", "workout_date"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.workout_date}"
