from rest_framework import serializers

class WorkoutPlanGenerateSerializer(serializers.Serializer):
    goal = serializers.ChoiceField(choices=["hypertrophy", "fat_loss"], default="hypertrophy")
    days_per_week = serializers.IntegerField(min_value=3, max_value=6)
    session_minutes = serializers.IntegerField(min_value=20, max_value=120)

    # tùy chọn: ưu tiên nhóm cơ
    focus_muscles = serializers.CharField(required=False, allow_blank=True, default="")
    seed = serializers.IntegerField(required=False)  # để plan ổn định nếu bạn muốn
