from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserPreferences, UserProfile
from .serializers import ProfileBundleSerializer, UserPreferencesSerializer, UserProfileSerializer
from .services.advice import profile_advice
from .services.completeness import require_complete_profile_data
from .services.dashboard import dashboard_greeting
from .services.metrics import calculate_metrics
from .services.weather import update_profile_weather


def ensure_profile_bundle(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    preferences, _ = UserPreferences.objects.get_or_create(user=user)
    return profile, preferences


def _serialized_profile(profile, request=None):
    return UserProfileSerializer(profile, context={"request": request}).data


def save_metrics_snapshot(profile, request=None):
    metrics = calculate_metrics(_serialized_profile(profile, request))
    profile.metrics_snapshot = metrics
    profile.metrics_updated_at = timezone.now()
    profile.save(update_fields=["metrics_snapshot", "metrics_updated_at", "updated_at"])
    return metrics


class ProfileView(APIView):
    def get(self, request):
        profile, preferences = ensure_profile_bundle(request.user)
        if not profile.metrics_snapshot:
            save_metrics_snapshot(profile, request)
        return Response(ProfileBundleSerializer({"profile": profile, "preferences": preferences}).data)

    def put(self, request):
        return self._save(request, partial=False)

    def patch(self, request):
        return self._save(request, partial=True)

    def _save(self, request, partial):
        profile, preferences = ensure_profile_bundle(request.user)
        profile_serializer = UserProfileSerializer(
            profile,
            data=request.data.get("profile", request.data),
            partial=partial,
        )
        preferences_serializer = UserPreferencesSerializer(
            preferences,
            data=request.data.get("preferences", {}),
            partial=True,
        )
        profile_serializer.is_valid(raise_exception=True)
        preferences_serializer.is_valid(raise_exception=True)
        profile = profile_serializer.save()
        preferences_serializer.save()
        save_metrics_snapshot(profile, request)
        return Response(ProfileBundleSerializer({"profile": profile, "preferences": preferences}).data)


class ProfileAdviceView(APIView):
    def post(self, request):
        profile, preferences = ensure_profile_bundle(request.user)
        profile_data = request.data.get("profile") or _serialized_profile(profile, request)
        pref_data = request.data.get("preferences") or UserPreferencesSerializer(preferences).data
        require_complete_profile_data(profile_data)
        metrics_from_request = request.data.get("metrics")
        metrics = metrics_from_request or profile.metrics_snapshot or calculate_metrics(profile_data)
        medical = request.data.get("medical") or {"conditions": pref_data.get("medical_conditions", [])}
        advice = profile_advice(profile_data, metrics, pref_data, medical)
        profile.metrics_snapshot = metrics
        profile.metrics_updated_at = timezone.now() if metrics_from_request else (profile.metrics_updated_at or timezone.now())
        profile.advice_snapshot = advice
        profile.advice_updated_at = timezone.now()
        profile.save(
            update_fields=[
                "metrics_snapshot",
                "metrics_updated_at",
                "advice_snapshot",
                "advice_updated_at",
                "updated_at",
            ]
        )
        return Response(advice)


class DashboardGreetingView(APIView):
    def get(self, request):
        profile, _ = ensure_profile_bundle(request.user)
        return Response(dashboard_greeting(profile))


class ProfileWeatherView(APIView):
    def post(self, request):
        profile, preferences = ensure_profile_bundle(request.user)
        try:
            update_profile_weather(profile, request.data)
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": f"Could not fetch weather: {str(exc)[:200]}"}, status=status.HTTP_502_BAD_GATEWAY)
        bundle = ProfileBundleSerializer({"profile": profile, "preferences": preferences}).data
        bundle["dashboard_greeting"] = dashboard_greeting(profile)
        return Response(bundle)
