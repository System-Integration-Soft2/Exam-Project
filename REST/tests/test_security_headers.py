"""Tests for SecurityHeadersMiddleware: nosniff on all responses, strict CSP on regular
endpoints, relaxed CSP on doc routes (/docs, /openapi.json, /redoc)."""

import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET


def _env(monkeypatch, tmp_path):
    db_path = str(tmp_path / "headers_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")


def _fresh_app(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    sys.modules.pop("app.main", None)

    async def mock_init_db(settings, seed_sql_path=None):
        pass

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):
        from app.main import app
        return app, mock_redis


def test_nosniff_on_healthz(monkeypatch, tmp_path):
    """X-Content-Type-Options: nosniff is present on a regular endpoint."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/healthz")
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_nosniff_on_docs(monkeypatch, tmp_path):
    """X-Content-Type-Options: nosniff is present on /docs."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/docs")
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_nosniff_on_openapi_json(monkeypatch, tmp_path):
    """X-Content-Type-Options: nosniff is present on /openapi.json."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/openapi.json")
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_nosniff_on_redoc(monkeypatch, tmp_path):
    """X-Content-Type-Options: nosniff is present on /redoc."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/redoc")
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_strict_csp_on_regular_endpoint(monkeypatch, tmp_path):
    """Regular endpoints get the strict CSP (contains default-src 'none', no CDN host)."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/healthz")
    csp = response.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp
    assert "cdn.jsdelivr.net" not in csp


def test_relaxed_csp_on_docs(monkeypatch, tmp_path):
    """The /docs route gets the relaxed CSP that includes the Swagger CDN host."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/docs")
    csp = response.headers.get("content-security-policy", "")
    assert "cdn.jsdelivr.net" in csp


def test_relaxed_csp_on_openapi_json(monkeypatch, tmp_path):
    """The /openapi.json route gets the relaxed CSP."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/openapi.json")
    csp = response.headers.get("content-security-policy", "")
    assert "cdn.jsdelivr.net" in csp


def test_relaxed_csp_on_redoc(monkeypatch, tmp_path):
    """The /redoc route gets the relaxed CSP."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/redoc")
    csp = response.headers.get("content-security-policy", "")
    assert "cdn.jsdelivr.net" in csp


def test_docs_returns_html_with_swagger_bundle(monkeypatch, tmp_path):
    """GET /docs returns 200 with HTML body referencing the SwaggerUI bundle."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    # FastAPI's Swagger UI loads from cdn.jsdelivr.net
    assert "cdn.jsdelivr.net" in response.text
