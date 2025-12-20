"""Security headers middleware for protecting against common web vulnerabilities."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-XSS-Protection: 1; mode=block (legacy XSS protection)
    - Strict-Transport-Security: HSTS for HTTPS enforcement (production only)
    - Content-Security-Policy: Restrict content sources
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Disable unnecessary browser features
    """

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response: Response = await call_next(request)

        # Prevent clickjacking - don't allow site to be framed
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS filter in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS - Force HTTPS for 1 year (only in production)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - disable unnecessary browser features
        permissions_directives = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        return response
