"""
Defense-in-depth response headers for every API response.

Identical contract to the SecurityHeadersMiddleware in auth-service — the
two are duplicated rather than shared because the services have no common
Python package. If a third service ever needs the same behaviour, this is
the moment to extract a shared library.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Headers set:
      • X-Content-Type-Options: nosniff
            Stops browsers from MIME-sniffing a response away from its
            declared Content-Type — closes the LOW finding ZAP raises on
            every endpoint of a default FastAPI app.

      • X-Frame-Options: DENY
            Prevents the page being iframed (clickjacking). Safe to set
            DENY on a JSON API — there's no legitimate iframe use.

      • Referrer-Policy: strict-origin-when-cross-origin
            Don't leak full URLs (which can contain tokens in querystrings)
            to external sites the user navigates to.

      • Permissions-Policy: camera=(), microphone=(), geolocation=()
            Disable browser APIs the API doesn't use.

    `setdefault` is used so individual routes can still override a header
    when they have a good reason (e.g. an HTML preview endpoint).
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        return response
