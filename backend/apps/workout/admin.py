from django.contrib import admin

from .models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "body_part_raw", "level", "embedding_model")
    search_fields = ("title", "body_part_raw")
    list_filter = ("body_part_raw", "level", "embedding_model")

