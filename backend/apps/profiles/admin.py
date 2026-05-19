from django.contrib import admin

from .models import UserPreferences, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "sex", "height_cm", "weight_kg", "goal_type", "updated_at")
    search_fields = ("user__username", "full_name")
    list_filter = ("sex", "activity_level", "experience_level", "goal_type")


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "dietary_style")
    search_fields = ("user__username",)
    list_filter = ("dietary_style",)

