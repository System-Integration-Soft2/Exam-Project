import pytest


TEST_JWT_SECRET = "test_jwt_secret_for_testing_32ch"


@pytest.fixture(autouse=False)
def valid_env(monkeypatch):
    """
    Monkeypatch a minimal valid environment for Settings instantiation.

    Use this fixture in any test that imports Settings directly.
    Tests in test_config.py manage their own env vars to exercise edge cases.
    """
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_SECONDS", "900")
    monkeypatch.setenv("REFRESH_TOKEN_TTL_SECONDS", "604800")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
