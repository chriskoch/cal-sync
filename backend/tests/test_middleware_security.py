"""
Tests for security headers middleware.

Verifies that all security headers are correctly set on responses
to protect against common web vulnerabilities.
"""
import pytest
from fastapi.testclient import TestClient


def test_security_headers_present_on_root(client):
    """Verify all security headers are set on root endpoint."""
    response = client.get("/")

    # Basic security headers (always present)
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"

    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"

    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_x_frame_options_denies_framing(client):
    """Verify X-Frame-Options prevents clickjacking."""
    response = client.get("/")
    assert response.headers["X-Frame-Options"] == "DENY"


def test_x_content_type_options_prevents_sniffing(client):
    """Verify X-Content-Type-Options prevents MIME sniffing."""
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_xss_protection_enabled(client):
    """Verify XSS protection is enabled for legacy browsers."""
    response = client.get("/")
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


def test_csp_header_value(client):
    """Verify CSP header restricts unsafe sources."""
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]

    # Check key CSP directives
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp


def test_csp_allows_inline_styles(client):
    """Verify CSP allows inline styles (required for React/MUI)."""
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]
    assert "style-src 'self' 'unsafe-inline'" in csp


def test_csp_allows_data_images(client):
    """Verify CSP allows data URIs for images."""
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]
    assert "img-src 'self' data: https:" in csp


def test_referrer_policy_set(client):
    """Verify Referrer-Policy controls referrer information."""
    response = client.get("/")
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_permissions_policy_disables_features(client):
    """Verify Permissions-Policy disables unnecessary browser features."""
    response = client.get("/")
    permissions = response.headers["Permissions-Policy"]

    # Check that sensitive features are disabled
    assert "geolocation=()" in permissions
    assert "microphone=()" in permissions
    assert "camera=()" in permissions
    assert "payment=()" in permissions
    assert "usb=()" in permissions


def test_security_headers_on_api_endpoints(client, auth_headers):
    """Verify security headers present on authenticated API responses."""
    response = client.get("/api/auth/me", headers=auth_headers)

    # Should have security headers regardless of authentication status
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_security_headers_on_unauthenticated_api(client):
    """Verify security headers present on unauthenticated API requests."""
    response = client.get("/api/auth/me")

    # Should have security headers even when request fails auth
    assert response.status_code == 401
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers


def test_security_headers_on_404_responses(client):
    """Verify security headers present even on error responses."""
    response = client.get("/nonexistent-route")

    # Should have security headers even on 404 errors
    assert response.status_code == 404
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_security_headers_on_health_check(client):
    """Verify security headers present on health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers


def test_hsts_header_not_in_development(client, monkeypatch):
    """Verify HSTS header is NOT set in development environment."""
    # The test environment defaults to development
    response = client.get("/")

    # HSTS should NOT be present in development
    assert "Strict-Transport-Security" not in response.headers


def test_security_headers_on_post_requests(client, auth_headers):
    """Verify security headers present on POST requests."""
    response = client.post(
        "/api/sync/config",
        headers=auth_headers,
        json={
            "source_calendar_id": "test@example.com",
            "dest_calendar_id": "dest@example.com",
        }
    )

    # Should have security headers on all HTTP methods
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_security_headers_consistent_across_routes(client):
    """Verify security headers are consistent across different routes."""
    routes = ["/", "/health"]
    headers_to_check = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Content-Security-Policy",
        "Referrer-Policy",
        "Permissions-Policy",
    ]

    responses = [client.get(route) for route in routes]

    # All routes should have the same security headers
    for header in headers_to_check:
        values = [r.headers.get(header) for r in responses]
        assert all(v == values[0] for v in values), f"{header} inconsistent across routes"
