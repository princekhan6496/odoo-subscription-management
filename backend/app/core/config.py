from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Brightloop Subscription Management"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/brightloop"
    secret_key: str = Field(default="dev-only-change-this-secret-key-before-deploying-2026", min_length=32)
    access_token_expire_minutes: int = 30
    access_cookie_name: str = "brightloop_access"
    csrf_cookie_name: str = "brightloop_csrf"
    cookie_domain: str | None = None
    cors_origins: str = "http://localhost:3000"
    allow_admin_bootstrap: bool = False
    frontend_url: str = "http://localhost:3000"
    resend_api_key: str | None = None
    email_from: str | None = None
    qstash_current_signing_key: str | None = None
    qstash_next_signing_key: str | None = None
    qstash_token: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)
    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment == "production":
            if self.secret_key.startswith("dev-only-"):
                raise ValueError("SECRET_KEY must be replaced in production")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production DATABASE_URL must use managed PostgreSQL with psycopg")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
