"""
Request logging middleware for admin.celiyo.com.

Logs every incoming HTTP request with:
- method, path, status_code, duration_ms
- user email (if authenticated)
- tenant info (from JWT or user object)

Logs go to the `apps` logger → logs/info.log and logs/error.log.
Do NOT log request bodies (contains passwords, PHI).
"""

import time
from apps.common.logger import get_logger

log = get_logger("apps.requests")


class RequestLoggingMiddleware:
    """Structured per-request logging for every API call."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start) * 1000, 1)

        # Resolve user info safely (middleware runs before auth in some configs)
        user_email = None
        user_id = None
        tenant_slug = None

        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            user_email = getattr(user, "email", None)
            user_id = str(user.pk) if hasattr(user, "pk") else None
            tenant = getattr(user, "tenant", None)
            if tenant:
                tenant_slug = getattr(tenant, "slug", None)

        status = response.status_code
        level = "error" if status >= 500 else "warning" if status >= 400 else "info"

        getattr(log, level)(
            "api_request",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": status,
                "duration_ms": duration_ms,
                "user_email": user_email,
                "user_id": user_id,
                "tenant_slug": tenant_slug,
                "query_string": request.META.get("QUERY_STRING", "") or None,
            },
        )

        return response
