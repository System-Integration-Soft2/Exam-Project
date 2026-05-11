import pytest
from pydantic import ValidationError

from tests.conftest import TEST_JWT_SECRET


def make_valid_env(**overrides):
    """Return a minimal valid env dict for Settings.

    DATABASE_PATH uses /tmp so the parent-exists validator passes in CI
    and local environments where /data is not mounted.
    """
    base = {
        "JWT_SECRET": TEST_JWT_SECRET,
        "DATABASE_PATH": "/tmp/catalog.db",
        "REDIS_URL": "redis://redis:6379/0",
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "604800",
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000",
        "SEED_ADMIN_USERNAME": "admin",
        "SEED_ADMIN_EMAIL": "admin@example.com",
        "SEED_ADMIN_PASSWORD": "admin123",
        "LOG_LEVEL": "INFO",
    }
    base.update(overrides)
    return base


def build_settings(monkeypatch, **overrides):
    """Monkeypatch env vars and instantiate Settings without loading .env."""
    from app.config import Settings

    env = make_valid_env(**overrides)
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    return Settings(_env_file=None)


class TestJwtSecretValidation:
    def test_jwt_secret_below_32_chars_raises(self, monkeypatch):
        """JWT_SECRET shorter than 32 chars must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env(JWT_SECRET="short_secret_31_chars_xxxxxxxxx")
        assert len(env["JWT_SECRET"]) == 31
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        assert "JWT_SECRET" in str(exc_info.value) or "jwt_secret" in str(exc_info.value).lower()

    def test_jwt_secret_exactly_32_chars_accepted(self, monkeypatch):
        """JWT_SECRET of exactly 32 chars is the minimum valid value."""
        settings = build_settings(monkeypatch, JWT_SECRET="a" * 32)
        assert len(settings.JWT_SECRET) == 32

    def test_jwt_secret_unset_raises(self, monkeypatch):
        """JWT_SECRET has no default; missing env var must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env()
        env.pop("JWT_SECRET")
        monkeypatch.delenv("JWT_SECRET", raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        assert "JWT_SECRET" in str(exc_info.value) or "jwt_secret" in str(exc_info.value).lower()


class TestDatabasePathValidation:
    def test_database_path_parent_must_exist(self, monkeypatch):
        """DATABASE_PATH whose parent directory does not exist must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env(DATABASE_PATH="/nonexistent_dir_xyz/catalog.db")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        assert "DATABASE_PATH" in str(exc_info.value) or "database_path" in str(exc_info.value).lower()

    def test_database_path_existing_parent_accepted(self, monkeypatch):
        """DATABASE_PATH whose parent directory exists is accepted."""
        settings = build_settings(monkeypatch, DATABASE_PATH="/tmp/catalog.db")
        assert settings.DATABASE_PATH == "/tmp/catalog.db"


class TestCorsOriginsValidation:
    def test_valid_cors_origin_accepted(self, monkeypatch):
        """A valid CORS origin string is accepted."""
        settings = build_settings(monkeypatch, CORS_ALLOWED_ORIGINS="http://localhost:3000")
        assert settings.CORS_ALLOWED_ORIGINS == "http://localhost:3000"

    def test_multiple_cors_origins_accepted(self, monkeypatch):
        """Comma-separated origins are accepted as a string."""
        origins = "http://localhost:3000,http://localhost:4000"
        settings = build_settings(monkeypatch, CORS_ALLOWED_ORIGINS=origins)
        assert settings.CORS_ALLOWED_ORIGINS == origins

    def test_cors_wildcard_rejected(self, monkeypatch):
        """CORS_ALLOWED_ORIGINS='*' must raise ValidationError.

        Wildcard origins with credentials are a browser security error;
        every origin must be named explicitly.
        """
        from app.config import Settings

        env = make_valid_env(CORS_ALLOWED_ORIGINS="*")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        assert "CORS" in str(exc_info.value) or "cors" in str(exc_info.value).lower()

    def test_cors_wildcard_in_list_rejected(self, monkeypatch):
        """A wildcard mixed into a comma-separated list must also be rejected."""
        from app.config import Settings

        env = make_valid_env(CORS_ALLOWED_ORIGINS="http://localhost:3000,*")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError):
            Settings(_env_file=None)


class TestTokenTtlValidation:
    def test_access_token_ttl_below_minimum_raises(self, monkeypatch):
        """ACCESS_TOKEN_TTL_SECONDS < 60 must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env(ACCESS_TOKEN_TTL_SECONDS="59")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_access_token_ttl_above_maximum_raises(self, monkeypatch):
        """ACCESS_TOKEN_TTL_SECONDS > 3600 must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env(ACCESS_TOKEN_TTL_SECONDS="3601")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_refresh_token_ttl_below_minimum_raises(self, monkeypatch):
        """REFRESH_TOKEN_TTL_SECONDS < 3600 must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env(REFRESH_TOKEN_TTL_SECONDS="3599")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_refresh_token_ttl_above_maximum_raises(self, monkeypatch):
        """REFRESH_TOKEN_TTL_SECONDS > 2592000 must raise ValidationError."""
        from app.config import Settings

        env = make_valid_env(REFRESH_TOKEN_TTL_SECONDS="2592001")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        with pytest.raises(ValidationError):
            Settings(_env_file=None)


class TestSettingsDefaults:
    def test_defaults_are_applied_when_not_overridden(self, monkeypatch):
        """Settings instantiated with only JWT_SECRET uses all documented defaults."""
        settings = build_settings(monkeypatch)
        assert settings.DATABASE_PATH == "/tmp/catalog.db"
        assert settings.REDIS_URL == "redis://redis:6379/0"
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_TTL_SECONDS == 900
        assert settings.REFRESH_TOKEN_TTL_SECONDS == 604800
        assert settings.CORS_ALLOWED_ORIGINS == "http://localhost:3000"
        assert settings.SEED_ADMIN_USERNAME == "admin"
        assert settings.SEED_ADMIN_EMAIL == "admin@example.com"
        assert settings.SEED_ADMIN_PASSWORD == "admin123"
        assert settings.LOG_LEVEL == "INFO"
