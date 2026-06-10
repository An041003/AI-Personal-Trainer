import json
import hashlib
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


SENSITIVE_KEYS = {"authorization", "password", "token", "api_key", "secret", "access", "refresh"}
MAX_CAPTURE_CHARS = 50000


def _is_sensitive_key(key):
    normalized = str(key or "").lower()
    return any(item in normalized for item in SENSITIVE_KEYS)


def _redact(value):
    if isinstance(value, dict):
        return {key: "***REDACTED***" if _is_sensitive_key(key) else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _json_or_summary(raw):
    if raw is None:
        return {}
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not raw:
        return {}
    if len(raw) > MAX_CAPTURE_CHARS:
        return {"_truncated": True, "preview": raw[:MAX_CAPTURE_CHARS]}
    try:
        return _redact(json.loads(raw))
    except (TypeError, ValueError):
        return {"_raw": raw[:MAX_CAPTURE_CHARS]}


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _token_user(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Token "):
        return None
    try:
        from rest_framework.authtoken.models import Token

        token = auth_header.split(" ", 1)[1].strip()
        return Token.objects.select_related("user").get(key=token).user
    except Exception:
        return None


def _token_key(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Token "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _should_log(request):
    path = request.path or ""
    if not path.startswith("/api/"):
        return False
    return not path.startswith(("/api/docs/", "/api/schema/"))


def _is_api_request(request):
    return (request.path or "").startswith("/api/")


def _should_rate_limit(request):
    path = request.path or ""
    if not _is_api_request(request):
        return False
    return not path.startswith(("/api/docs/", "/api/schema/"))


def _rate_scope(request):
    path = request.path or ""
    if path.startswith(("/api/auth/login/", "/api/auth/register/")):
        return "auth"
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return "read"
    if any(
        marker in path
        for marker in (
            "/intent/analyze/",
            "/plan/generate/",
            "/plan/generate-from-goal/",
            "/plan/replace/",
            "/plan/replace-exercise/",
            "/profile/advice/",
            "/profile/dashboard-greeting/",
        )
    ):
        return "ai"
    return "default"


def _parse_rate(value, fallback):
    try:
        limit, window = str(value).split("/", 1)
        return max(int(limit), 1), max(int(window), 1)
    except (TypeError, ValueError):
        return fallback


def _rate_for_scope(scope):
    rates = getattr(settings, "AIPT_RATE_LIMITS", {})
    fallback = (240, 60)
    return _parse_rate(rates.get(scope), _parse_rate(rates.get("default"), fallback))


def _rate_identity(request):
    token_key = _token_key(request)
    if token_key:
        return f"token:{token_key}"
    ip = _client_ip(request) or "unknown"
    return f"ip:{hashlib.sha256(ip.encode('utf-8')).hexdigest()[:24]}"


class RateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not getattr(settings, "AIPT_RATE_LIMIT_ENABLED", True) or not _should_rate_limit(request):
            return None

        scope = _rate_scope(request)
        limit, window = _rate_for_scope(scope)
        bucket = int(time.time() // window)
        key = f"aipt:rate:{scope}:{_rate_identity(request)}:{bucket}"

        try:
            added = cache.add(key, 1, timeout=window + 5)
            count = 1 if added else cache.incr(key)
        except Exception:
            return None

        if count > limit:
            return JsonResponse(
                {
                    "detail": "Too many requests. Please wait before trying again.",
                    "rate_limit": {"scope": scope, "limit": limit, "window_seconds": window},
                },
                status=429,
            )
        return None


class CurrentUserRLSMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not getattr(settings, "AIPT_RLS_ENABLED", True) or not _is_api_request(request):
            return None

        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            user = _token_user(request)

        user_id = str(user.id) if getattr(user, "is_authenticated", False) else ""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.current_user_id', %s, false)", [user_id])
            request._aipt_rls_active = True
        except Exception:
            request._aipt_rls_active = False
        return None

    def _reset(self, request):
        if not getattr(request, "_aipt_rls_active", False):
            return
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET app.current_user_id")
        except Exception:
            pass

    def process_response(self, request, response):
        self._reset(request)
        return response

    def process_exception(self, request, exception):
        self._reset(request)
        return None


class ApiRequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._aipt_started_at = time.perf_counter()
        request._aipt_request_body = {}
        if _should_log(request):
            try:
                request._aipt_request_body = _json_or_summary(request.body)
            except Exception:
                request._aipt_request_body = {"_unavailable": True}
        return None

    def process_response(self, request, response):
        if not _should_log(request):
            return response

        try:
            from apps.common.models import ApiRequestLog

            content_type = response.get("Content-Type", "")
            response_body = {}
            if "application/json" in content_type and not getattr(response, "streaming", False):
                response_body = _json_or_summary(response.content)

            user = getattr(request, "user", None)
            if not getattr(user, "is_authenticated", False):
                user = _token_user(request)

            duration_ms = None
            started_at = getattr(request, "_aipt_started_at", None)
            if started_at:
                duration_ms = int((time.perf_counter() - started_at) * 1000)

            ApiRequestLog.objects.create(
                user=user if getattr(user, "is_authenticated", False) else None,
                method=request.method,
                path=request.path,
                query_params=_redact(dict(request.GET)),
                status_code=response.status_code,
                request_body=getattr(request, "_aipt_request_body", {}),
                response_body=response_body,
                ip_address=_client_ip(request),
                duration_ms=duration_ms,
            )
        except Exception:
            pass

        return response
