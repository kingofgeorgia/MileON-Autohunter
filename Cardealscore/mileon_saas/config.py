from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MileON Cars SaaS"
    environment: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./mileon_saas.db"
    default_company_id: int = 1
    api_base_url: str = "http://127.0.0.1:8000"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_path: str = "/telegram/webhook"

    ml_model_path: str = "./ml_model.joblib"
    ml_metadata_path: str = "./ml_metadata.json"
    ml_confidence_threshold: float = 0.75

    model_config = SettingsConfigDict(env_prefix="MILEON_", case_sensitive=False)


settings = Settings()
