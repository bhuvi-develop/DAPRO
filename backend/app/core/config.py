"""12-factor configuration. Every secret comes from the environment (INT-COM-02, NFR-SEC-05)."""
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT = "change-me-in-env-change-me-in-env-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAPRO_", env_file=None, extra="ignore")

    env: str = Field("development", description="demo | development | test | production")
    database_url: str = "postgresql+psycopg://dapro_app:dapro_app@localhost:5432/dapro"
    database_owner_url: str = "postgresql+psycopg://dapro_owner:dapro_owner@localhost:5432/dapro"
    app_db_password: str = "dapro_app"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = _DEFAULT_JWT
    access_token_minutes: int = 15
    refresh_token_hours: int = 12
    session_idle_minutes: int = 60
    cors_origins: str = "http://localhost:8480"
    cookie_secure: bool = False
    demo_password: str = "Demo@12345"
    email_mode: str = "mock"
    sms_mode: str = "mock"
    bank_adapter: str = "mock"
    field_location_capture_enabled: bool = False
    login_rate_per_minute: int = 20
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    storage_dir: str = "/app/storage"
    celery_eager: bool = False
    max_upload_mb: int = 10
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _refuse_insecure_defaults(self) -> "Settings":
        """Outside demo/development/test, refuse to start with built-in defaults or weak secrets (NFR-SEC-05)."""
        if self.env in ("demo", "development", "test"):
            return self
        problems = []
        if self.jwt_secret == _DEFAULT_JWT or len(self.jwt_secret) < 32:
            problems.append("DAPRO_JWT_SECRET must be set to a random value of at least 32 characters")
        if self.app_db_password == "dapro_app" or "dapro_app:dapro_app@" in self.database_url:
            problems.append("DAPRO_APP_DB_PASSWORD / DAPRO_DATABASE_URL still use the default password")
        if "dapro_owner:dapro_owner@" in self.database_owner_url:
            problems.append("DAPRO_DATABASE_OWNER_URL still uses the default password")
        if not self.cookie_secure:
            problems.append("DAPRO_COOKIE_SECURE must be true (refresh cookie over HTTPS only)")
        if self.email_mode == "mock" or self.sms_mode == "mock" or self.bank_adapter == "mock":
            problems.append("MOCK providers are not allowed outside demo; set DAPRO_*_MODE / DAPRO_BANK_ADAPTER explicitly")
        if problems:
            raise ValueError(f"Insecure configuration for env '{self.env}': " + "; ".join(problems))
        return self

    @property
    def is_demo(self) -> bool:
        return self.env in ("demo", "development", "test")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
