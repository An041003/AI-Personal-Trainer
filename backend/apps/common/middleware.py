import json
import time

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


def _should_log(request):
    path = request.path or ""
    if not path.startswith("/api/"):
        return False
    return not path.startswith(("/api/docs/", "/api/schema/"))


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
