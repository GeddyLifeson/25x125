from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables or a .env file in the repo root (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/x25x125"
    socrata_app_token: str = ""
    census_api_key: str = ""

    # "development" (default) or "production". Production refuses the dev fallbacks below.
    app_env: str = "development"
    # Shared with the web app; signs the user and organization the web app sends on each engine call.
    engine_shared_secret: str = ""
    # Sign-in email. SMTP URL such as smtp://user:password@smtp.example.com:587; empty = dev mode
    # (sign-in links go to the engine console and to .dev-mail/ instead of an inbox).
    email_server: str = ""
    email_from: str = "25x125 <sign-in@localhost>"
    # Stripe (test mode keys while building). Empty = billing routes answer 503 with a plain note.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_founding_monthly: str = ""
    # Error tracking. Empty = errors are only logged.
    sentry_dsn: str = ""


settings = Settings()
