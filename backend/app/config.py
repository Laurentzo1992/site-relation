from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://siterelation:siterelation@localhost:5432/siterelation"
    secret_key: str = "change-me-to-a-long-random-string"
    admin_session_secret: str = "change-me-too-another-long-random-string"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    ad_price: int = 500
    connection_request_price: int = 500
    currency: str = "XOF"

    cors_origins: str = "http://localhost:5173"

    # "mock" (default, no external calls, useful for local dev) or "ligdicash"
    payment_provider: str = "mock"
    ligdicash_base_url: str = "https://app.ligdicash.com"
    ligdicash_api_key: str = ""
    ligdicash_auth_token: str = ""

    # Used to build the URLs LigdiCash redirects/calls back to. Must be
    # publicly reachable for callback_url when payment_provider=ligdicash.
    public_backend_url: str = "http://localhost:8000"
    public_frontend_url: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
