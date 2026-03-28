from django.conf import settings
from django.core.cache import cache


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _normalize_identity(identity):
    return (identity or "anonymous").strip().lower().replace(" ", "_")


def build_rate_limit_key(scope, request, identity=""):
    return f"qvatel:rate-limit:{scope}:{get_client_ip(request)}:{_normalize_identity(identity)}"


def is_rate_limited(scope, request, identity=""):
    attempts = cache.get(build_rate_limit_key(scope, request, identity), 0)
    return attempts >= settings.AUTH_RATE_LIMIT_ATTEMPTS


def record_rate_limit_failure(scope, request, identity=""):
    key = build_rate_limit_key(scope, request, identity)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)
    return attempts


def clear_rate_limit(scope, request, identity=""):
    cache.delete(build_rate_limit_key(scope, request, identity))
