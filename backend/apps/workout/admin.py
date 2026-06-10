from django.contrib import admin

from .models import Exercise, WorkoutCompletion


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "body_part_raw", "level", "embedding_model")
    search_fields = ("title", "body_part_raw")
    list_filter = ("body_part_raw", "level", "embedding_model")


@admin.register(WorkoutCompletion)
class WorkoutCompletionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "workout_date", "plan", "created_at")
    list_filter = ("workout_date", "created_at")
    search_fields = ("user__username", "user__email")
