from rest_framework import serializers

from .models import UserPreferences, UserProfile
from .services.completeness import profile_completeness


class UserProfileSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "full_name",
            "avatar",
            "sex",
            "birth_year",
            "age",
            "height_cm",
            "weight_kg",
            "waist_cm",
            "neck_cm",
            "hip_cm",
            "activity_level",
            "experience_level",
            "goal_type",
            "focus_muscles",
            "country",
            "city",
            "latitude",
            "longitude",
            "location_source",
            "weather_snapshot",
            "weather_updated_at",
            "dashboard_greeting_snapshot",
            "dashboard_greeting_updated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "age",
            "focus_muscles",
            "weather_snapshot",
            "weather_updated_at",
            "dashboard_greeting_snapshot",
            "dashboard_greeting_updated_at",
            "created_at",
            "updated_at",
        ]

    def get_age(self, obj):
        if not obj.birth_year:
            return None
        from datetime import date

        return max(date.today().year - obj.birth_year, 0)

    def update(self, instance, validated_data):
        location_fields = ["country", "city", "latitude", "longitude"]
        location_changed = any(
            field in validated_data and validated_data.get(field) != getattr(instance, field)
            for field in location_fields
        )
        if location_changed:
            validated_data["weather_snapshot"] = {}
            validated_data["weather_updated_at"] = None
        return super().update(instance, validated_data)


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = [
            "id",
            "dietary_style",
            "allergies",
            "disliked_foods",
            "favorite_foods",
            "avoid_ingredients",
            "medical_conditions",
            "notes",
        ]
        read_only_fields = ["id"]


class ProfileBundleSerializer(serializers.Serializer):
    profile = UserProfileSerializer()
    preferences = UserPreferencesSerializer()
    metrics = serializers.SerializerMethodField()
    advice = serializers.SerializerMethodField()
    metrics_updated_at = serializers.SerializerMethodField()
    advice_updated_at = serializers.SerializerMethodField()
    completeness = serializers.SerializerMethodField()

    def get_metrics(self, obj):
        return obj["profile"].metrics_snapshot or None

    def get_advice(self, obj):
        return obj["profile"].advice_snapshot or None

    def get_metrics_updated_at(self, obj):
        return obj["profile"].metrics_updated_at

    def get_advice_updated_at(self, obj):
        return obj["profile"].advice_updated_at

    def get_completeness(self, obj):
        return profile_completeness(obj["profile"])
