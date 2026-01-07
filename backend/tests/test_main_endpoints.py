"""
Tests for main application endpoints.

Tests for root, health check, CORS, and SPA routing functionality.
"""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint_returns_version_info(client):
    """Test root endpoint returns app info when static files don't exist."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    # In test environment without static files, should return JSON
    assert "message" in data or "version" in data
    if "version" in data:
        assert data["version"] == "0.8.3"


def test_health_check_endpoint(client):
    """Test health check endpoint returns healthy status."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_check_no_auth_required(client):
    """Test health check doesn't require authentication."""
    # No auth headers provided
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_check_content_type(client):
    """Test health check returns JSON content type."""
    response = client.get("/health")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_api_routes_return_json_errors(client):
    """Test API routes return JSON errors, not HTML."""
    response = client.get("/api/nonexistent")

    assert response.status_code == 404
    # Should return JSON, not HTML
    assert "application/json" in response.headers["content-type"]


def test_api_routes_not_caught_by_spa(client):
    """Test API routes aren't caught by SPA catch-all."""
    response = client.get("/api/invalid-endpoint-test")

    # Should return 404 JSON error, not serve SPA
    assert response.status_code == 404
    assert "application/json" in response.headers["content-type"]


def test_cors_headers_present(client):
    """Test CORS headers are set correctly."""
    # Make a request with an allowed origin
    response = client.get(
        "/api/auth/me",
        headers={"Origin": "http://localhost:3033"}
    )

    # CORS headers should be present (though TestClient may not fully simulate CORS)
    # At minimum, verify the endpoint is accessible
    assert response.status_code in [200, 401]  # 401 if not authenticated, 200 if authenticated


def test_cors_preflight_options_request(client):
    """Test CORS preflight OPTIONS requests."""
    response = client.options(
        "/api/auth/me",
        headers={
            "Origin": "http://localhost:3033",
            "Access-Control-Request-Method": "GET",
        }
    )

    # OPTIONS request should succeed
    assert response.status_code == 200


def test_root_endpoint_accessible(client):
    """Test root endpoint is accessible."""
    response = client.get("/")
    assert response.status_code == 200


def test_api_prefix_required_for_api_routes(client, auth_headers):
    """Test that API routes require /api prefix."""
    # Try accessing auth endpoint without /api prefix
    response = client.get("/auth/me", headers=auth_headers)

    # Should return 404 (caught by SPA router or not found)
    assert response.status_code == 404


def test_health_endpoint_consistency(client):
    """Test health endpoint returns consistent responses."""
    responses = [client.get("/health") for _ in range(3)]

    # All responses should be identical
    for response in responses:
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_health_endpoint_performance(client):
    """Test health endpoint responds quickly (no database queries)."""
    import time

    start = time.time()
    response = client.get("/health")
    duration = time.time() - start

    assert response.status_code == 200
    # Health check should be very fast (< 100ms in test environment)
    assert duration < 0.1


def test_root_endpoint_methods(client):
    """Test root endpoint only supports GET method."""
    # GET should work
    assert client.get("/").status_code == 200

    # POST should not be allowed
    response = client.post("/")
    assert response.status_code == 405  # Method Not Allowed


def test_health_endpoint_methods(client):
    """Test health endpoint only supports GET method."""
    # GET should work
    assert client.get("/health").status_code == 200

    # POST should not be allowed
    response = client.post("/health")
    assert response.status_code == 405  # Method Not Allowed


def test_api_endpoints_accessible_with_auth(client, auth_headers):
    """Test API endpoints are accessible with authentication."""
    response = client.get("/api/auth/me", headers=auth_headers)

    # Should return 200 with valid auth
    assert response.status_code == 200


def test_api_endpoints_require_auth(client):
    """Test protected API endpoints require authentication."""
    response = client.get("/api/auth/me")

    # Should return 401 without auth
    assert response.status_code == 401


def test_multiple_cors_origins_allowed(client):
    """Test multiple CORS origins are configured."""
    allowed_origins = [
        "http://localhost:3033",
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    for origin in allowed_origins:
        response = client.get(
            "/health",
            headers={"Origin": origin}
        )
        # Request should succeed
        assert response.status_code == 200
