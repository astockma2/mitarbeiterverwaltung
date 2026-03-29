from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Datenbank
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "mitarbeiterverwaltung"
    db_user: str = "app"
    db_password: str = ""
    db_use_sqlite: bool = True  # Fuer Entwicklung ohne PostgreSQL

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "dev-secret-key-CHANGE-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Active Directory
    ad_server: str = "ldap://dc01.klinik.local"
    ad_port: int = 389
    ad_use_ssl: bool = False
    ad_base_dn: str = "DC=klinik,DC=local"
    ad_user_search_base: str = "OU=Benutzer,DC=klinik,DC=local"
    ad_bind_user: str = ""
    ad_bind_password: str = ""
    ad_group_admin: str = "APP-Mitarbeiterverwaltung-Admin"
    ad_group_hr: str = "APP-Mitarbeiterverwaltung-HR"
    ad_group_manager: str = "APP-Mitarbeiterverwaltung-Leitung"
    ad_enabled: bool = False  # Deaktiviert fuer Entwicklung

    # App
    app_name: str = "Mitarbeiterverwaltung"
    app_env: str = "development"
    app_debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8000,http://localhost:8080,http://localhost:8090"

    @property
    def database_url(self) -> str:
        if self.db_use_sqlite:
            return "sqlite+aiosqlite:///./mitarbeiterverwaltung.db"
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        if self.db_use_sqlite:
            return "sqlite:///./mitarbeiterverwaltung.db"
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
