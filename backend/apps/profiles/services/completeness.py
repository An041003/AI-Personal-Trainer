from rest_framework.exceptions import ValidationError

from apps.profiles.models import UserProfile


REQUIRED_PROFILE_FIELDS = [
    ("sex", "Sex"),
    ("birth_year", "Birth year"),
    ("height_cm", "Height"),
    ("weight_kg", "Weight"),
    ("waist_cm", "Waist"),
    ("neck_cm", "Neck"),
    ("activity_level", "Activity level"),
    ("experience_level", "Experience level"),
    ("goal_type", "Goal type"),
]


def _value(source, key):
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def profile_missing_fields(profile):
    missing = [
        {"field": field, "label": label}
        for field, label in REQUIRED_PROFILE_FIELDS
        if _is_blank(_value(profile, field))
    ]
    if _value(profile, "sex") == "female" and _is_blank(_value(profile, "hip_cm")):
        missing.append({"field": "hip_cm", "label": "Hip"})
    return missing


def profile_completeness(profile):
    missing = profile_missing_fields(profile)
    total = len(REQUIRED_PROFILE_FIELDS) + (1 if _value(profile, "sex") == "female" else 0)
    completed = max(total - len(missing), 0)
    return {
        "is_complete": not missing,
        "missing_fields": missing,
        "completion_percent": round((completed / total) * 100) if total else 100,
    }


def require_complete_profile(user):
    try:
        profile = user.profile
    except (AttributeError, UserProfile.DoesNotExist):
        profile = {}

    completeness = profile_completeness(profile)
    if completeness["is_complete"]:
        return completeness

    raise ValidationError(
        {
            "detail": "Please complete your profile before using this feature.",
            "missing_profile_fields": completeness["missing_fields"],
        }
    )


def require_complete_profile_data(profile):
    completeness = profile_completeness(profile or {})
    if completeness["is_complete"]:
        return completeness

    raise ValidationError(
        {
            "detail": "Please complete your profile before using this feature.",
            "missing_profile_fields": completeness["missing_fields"],
        }
    )
