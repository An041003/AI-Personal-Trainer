from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    SEX_CHOICES = [("male", "Male"), ("female", "Female")]
    ACTIVITY_CHOICES = [
        ("sedentary", "Sedentary"),
        ("light", "Light"),
        ("moderate", "Moderate"),
        ("very_active", "Very active"),
        ("athlete", "Athlete"),
    ]
    EXPERIENCE_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    GOAL_CHOICES = [
        ("cut", "Cut"),
        ("bulk", "Bulk"),
        ("recomp", "Recomp"),
        ("maintain", "Maintain"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    waist_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    neck_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hip_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default="moderate")
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default="beginner")
    goal_type = models.CharField(max_length=20, choices=GOAL_CHOICES, default="recomp")
    goal_text = models.TextField(blank=True)
    focus_muscles = models.JSONField(default=list, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_source = models.CharField(max_length=20, blank=True)
    weather_snapshot = models.JSONField(default=dict, blank=True)
    weather_updated_at = models.DateTimeField(null=True, blank=True)
    metrics_snapshot = models.JSONField(default=dict, blank=True)
    metrics_updated_at = models.DateTimeField(null=True, blank=True)
    advice_snapshot = models.JSONField(default=dict, blank=True)
    advice_updated_at = models.DateTimeField(null=True, blank=True)
    dashboard_greeting_snapshot = models.JSONField(default=dict, blank=True)
    dashboard_greeting_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"

    def __str__(self):
        return self.full_name or self.user.username


class UserPreferences(models.Model):
    DIETARY_CHOICES = [
        ("none", "None"),
        ("vegetarian", "Vegetarian"),
        ("vegan", "Vegan"),
        ("halal", "Halal"),
        ("low_carb", "Low carb"),
        ("keto", "Keto"),
        ("mediterranean", "Mediterranean"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferences")
    dietary_style = models.CharField(max_length=30, choices=DIETARY_CHOICES, default="none")
    allergies = models.JSONField(default=list, blank=True)
    disliked_foods = models.JSONField(default=list, blank=True)
    favorite_foods = models.JSONField(default=list, blank=True)
    avoid_ingredients = models.JSONField(default=list, blank=True)
    medical_conditions = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "user_preferences"

    def __str__(self):
        return f"Preferences for {self.user.username}"
