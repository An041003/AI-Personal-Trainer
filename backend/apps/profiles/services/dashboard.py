import hashlib
import json
from datetime import timedelta, timezone as datetime_timezone

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.common.openai_client import generate_json
from apps.common.prompt import DASHBOARD_GREETING_SYSTEM_PROMPT


DASHBOARD_TIME_ZONE = datetime_timezone(timedelta(hours=7), "Asia/Saigon")


def _local_date(value=None):
    value = value or timezone.now()
    return timezone.localtime(value, DASHBOARD_TIME_ZONE).date()


def _weather_context(profile):
    weather = profile.weather_snapshot or {}
    current = weather.get("current") or {}
    location = weather.get("location") or {}
    condition = current.get("condition_text") or ""
    temp_c = current.get("temp_c")
    humidity = current.get("humidity")
    city = profile.city or location.get("city") or location.get("name") or ""
    country = profile.country or location.get("country") or ""

    return {
        "city": city,
        "country": country,
        "temp_c": temp_c,
        "humidity": humidity,
        "condition": condition,
        "updated_at": profile.weather_updated_at.isoformat() if profile.weather_updated_at else "",
    }


def _weather_digest(weather):
    return hashlib.sha256(json.dumps(weather, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _fallback_message(profile):
    weather = _weather_context(profile)
    place = ", ".join([item for item in [weather["city"], weather["country"]] if item])
    condition = weather["condition"]
    temp_c = weather["temp_c"]

    if place and temp_c is not None:
        weather_text = f"Thoi tiet o {place} khoang {round(float(temp_c))} do C"
        if condition:
            weather_text += f", {condition.lower()}"
        return f"{weather_text}, rat hop de an uong gon nhe va tap luyen nang suat hom nay."

    return "Hay cap nhat vi tri va thoi tiet de nhan goi y phu hop, chuc ban co mot ngay an uong va tap luyen nang suat."


def _stored_greeting(profile, today, digest):
    snapshot = profile.dashboard_greeting_snapshot or {}
    if snapshot.get("date") != today.isoformat():
        return None
    if snapshot.get("weather_digest") != digest:
        return None
    message = str(snapshot.get("message") or "").strip()
    if not message:
        return None
    return {
        "message": message,
        "generated_at": snapshot.get("generated_at") or "",
        "source": snapshot.get("source") or "stored",
    }


def _save_greeting(profile, response, today, digest):
    now = timezone.now()
    snapshot = {
        "date": today.isoformat(),
        "weather_digest": digest,
        "message": response["message"],
        "generated_at": now.isoformat(),
        "source": response.get("source") or "llm",
    }
    profile.dashboard_greeting_snapshot = snapshot
    profile.dashboard_greeting_updated_at = now
    profile.save(
        update_fields=[
            "dashboard_greeting_snapshot",
            "dashboard_greeting_updated_at",
            "updated_at",
        ]
    )
    return {
        "message": snapshot["message"],
        "generated_at": snapshot["generated_at"],
        "source": snapshot["source"],
    }


def dashboard_greeting(profile, *, force=False):
    weather = _weather_context(profile)
    today = _local_date()
    digest = _weather_digest(weather)
    cache_source = {
        "user_id": profile.user_id,
        "date": today.isoformat(),
        "weather_digest": digest,
        "goal_type": profile.goal_type,
        "activity_level": profile.activity_level,
    }
    cache_digest = hashlib.sha256(json.dumps(cache_source, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]
    cache_key = f"aipt:dashboard:greeting:{profile.user_id}:{cache_digest}"

    if not force:
        stored = _stored_greeting(profile, today, digest)
        if stored:
            cache.set(cache_key, stored, timeout=60 * 60 * 12)
            return stored
        cached = cache.get(cache_key)
        if cached:
            return cached

    payload = {
        "profile": {
            "name": profile.full_name or profile.user.username,
            "goal_type": profile.goal_type,
            "activity_level": profile.activity_level,
            "experience_level": profile.experience_level,
        },
        "weather": weather,
        "today": today.isoformat(),
        "style": "friendly, practical, energetic, Vietnamese",
    }

    try:
        result = generate_json(
            DASHBOARD_GREETING_SYSTEM_PROMPT,
            json.dumps(payload, ensure_ascii=True),
            max_retries=0,
        )
        message = str(result.get("message") or "").strip()
        source = "llm"
    except ImproperlyConfigured:
        message = _fallback_message(profile)
        source = "fallback"
    except Exception:
        message = _fallback_message(profile)
        source = "fallback"

    if not message:
        message = _fallback_message(profile)
        source = "fallback"

    response = _save_greeting(profile, {"message": message, "source": source}, today, digest)
    cache.set(cache_key, response, timeout=60 * 60 * 12)
    return response
