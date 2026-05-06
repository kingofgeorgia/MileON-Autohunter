from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "gcb_user"
    postgres_password: str = "gcb_password"
    postgres_db: str = "gcb_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    secret_key: str = "change_me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    frontend_origin: str = "http://localhost:3000"

    exchange_api_url: str = "https://open.er-api.com/v6/latest/USD"
    exchange_cache_ttl_seconds: int = 3600

    myauto_api_url: str = "https://api2.myauto.ge/ka"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
