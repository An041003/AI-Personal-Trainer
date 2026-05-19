from rest_framework import serializers

from .models import Exercise, WorkoutIntentAnalysis


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "id",
            "title",
            "body_part_raw",
            "muscle_groups",
            "equipment",
            "level",
            "image_url",
            "image_file",
        ]


class WorkoutIntentAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutIntentAnalysis
        fields = ["id", "goal_text", "focus_muscles", "created_at"]
        read_only_fields = ["id", "created_at"]
