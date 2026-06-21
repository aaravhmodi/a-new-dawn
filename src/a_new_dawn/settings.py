from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_db_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_issuer: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cli_api_base_url: str = "http://127.0.0.1:8000"
    cli_state_path: str = ".local/a-new-dawn-session.json"

    @property
    def cli_state_file(self) -> Path:
        return Path(self.cli_state_path)

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def resolved_supabase_jwt_issuer(self) -> str:
        return self.supabase_jwt_issuer or f"{self.supabase_url}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
