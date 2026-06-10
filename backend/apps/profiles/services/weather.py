import json
import math
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.common.utils import normalize_text


WEATHERAPI_CURRENT_URL = "https://api.weatherapi.com/v1/current.json"
GPS_SAME_CITY_RADIUS_KM = 50
SUBLOCALITY_MARKERS = {
    "district",
    "ward",
    "borough",
    "commune",
    "phuong",
    "quan",
    "huyen",
    "xa",
    "thi xa",
}
COUNTRIES_USE_REGION_AS_CITY_FOR_GPS = {"vietnam", "viet nam"}


def _decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _weather_query(*, latitude=None, longitude=None, country="", city=""):
    lat = _decimal_or_none(latitude)
    lon = _decimal_or_none(longitude)
    if lat is not None and lon is not None:
        return f"{lat},{lon}", "gps"

    city = str(city or "").strip()
    country = str(country or "").strip()
    if city and country:
        return f"{city}, {country}", "manual"
    if city:
        return city, "manual"
    return "", ""


def _norm(value):
    return normalize_text(value or "")


def _today(value):
    return bool(value and timezone.localdate(value) == timezone.localdate())


def _distance_km(lat_a, lon_a, lat_b, lon_b):
    values = [_decimal_or_none(item) for item in [lat_a, lon_a, lat_b, lon_b]]
    if any(item is None for item in values):
        return None
    lat1, lon1, lat2, lon2 = [math.radians(float(item)) for item in values]
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(hav))


def _snapshot_location(snapshot):
    return (snapshot or {}).get("location") or {}


def _cached_weather_matches(profile, payload, source):
    if not profile.weather_snapshot or not _today(profile.weather_updated_at):
        return False

    location = _snapshot_location(profile.weather_snapshot)
    if source == "manual":
        requested_city = _norm(payload.get("city"))
        requested_country = _norm(payload.get("country"))
        cached_city = _norm(profile.city or location.get("name"))
        cached_country = _norm(profile.country or location.get("country"))
        city_matches = requested_city and requested_city == cached_city
        country_matches = not requested_country or requested_country == cached_country
        return bool(city_matches and country_matches)

    if source == "gps":
        distance = _distance_km(
            payload.get("latitude"),
            payload.get("longitude"),
            profile.latitude or location.get("lat"),
            profile.longitude or location.get("lon"),
        )
        return distance is not None and distance <= GPS_SAME_CITY_RADIUS_KM

    return False


def _fetch_weather(query):
    api_key = getattr(settings, "WEATHERAPI_KEY", "")
    if not api_key:
        raise ImproperlyConfigured("WEATHERAPI_KEY is not configured.")

    url = f"{WEATHERAPI_CURRENT_URL}?{urlencode({'key': api_key, 'q': query, 'aqi': 'no'})}"
    request = Request(url, headers={"User-Agent": "AI-Personal-Trainer/0.1"})
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _snapshot(raw):
    location = raw.get("location") or {}
    current = raw.get("current") or {}
    condition = current.get("condition") or {}
    return {
        "location": {
            "name": location.get("name") or "",
            "region": location.get("region") or "",
            "country": location.get("country") or "",
            "lat": location.get("lat"),
            "lon": location.get("lon"),
            "localtime": location.get("localtime") or "",
        },
        "current": {
            "temp_c": current.get("temp_c"),
            "feelslike_c": current.get("feelslike_c"),
            "humidity": current.get("humidity"),
            "wind_kph": current.get("wind_kph"),
            "uv": current.get("uv"),
            "condition_text": condition.get("text") or "",
            "condition_icon": condition.get("icon") or "",
        },
    }


def _looks_like_sublocality(name):
    normalized = _norm(name)
    words = set(normalized.split())
    return any(marker in normalized if " " in marker else marker in words for marker in SUBLOCALITY_MARKERS)


def _coarse_city(location, source, payload):
    manual_city = str(payload.get("city") or "").strip()
    if source == "manual" and manual_city:
        return manual_city

    name = str(location.get("name") or "").strip()
    region = str(location.get("region") or "").strip()
    country = _norm(location.get("country"))

    if region and country in COUNTRIES_USE_REGION_AS_CITY_FOR_GPS:
        return region
    if region and _looks_like_sublocality(name):
        return region
    return name or region


def update_profile_weather(profile, payload):
    query, source = _weather_query(
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
        country=payload.get("country"),
        city=payload.get("city"),
    )
    if not query:
        raise ValueError("Provide latitude/longitude or city/country.")

    if _cached_weather_matches(profile, payload, source):
        return profile.weather_snapshot

    raw = _fetch_weather(query)
    snapshot = _snapshot(raw)
    location = snapshot.get("location") or {}
    lat = _decimal_or_none(location.get("lat")) or _decimal_or_none(payload.get("latitude"))
    lon = _decimal_or_none(location.get("lon")) or _decimal_or_none(payload.get("longitude"))
    city = _coarse_city(location, source, payload)
    country = str(payload.get("country") or location.get("country") or "").strip()

    snapshot["location"]["city"] = city
    snapshot["location"]["country"] = country

    profile.city = city
    profile.country = country
    profile.latitude = lat
    profile.longitude = lon
    profile.location_source = source
    profile.weather_snapshot = snapshot
    profile.weather_updated_at = timezone.now()
    profile.save(
        update_fields=[
            "city",
            "country",
            "latitude",
            "longitude",
            "location_source",
            "weather_snapshot",
            "weather_updated_at",
            "updated_at",
        ]
    )
    try:
        from apps.profiles.services.dashboard import dashboard_greeting

        dashboard_greeting(profile, force=True)
    except Exception:
        pass
    return snapshot
