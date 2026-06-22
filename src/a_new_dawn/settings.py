from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_db_url: str
    supabase_url: str
    supabase_publishable_key: str = ""
    supabase_anon_key: str = ""
    supabase_secret_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None
    llm_provider: str = "modelrelay"
    openai_api_key: str | None = None
    openai_model: str = "auto-fastest"
    openai_base_url: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    modelrelay_base_url: str = "http://127.0.0.1:7352/v1"
    modelrelay_api_key: str = "dummy-key"
    modelrelay_model: str = "auto-fastest"
    ollama_base_url: str = "http://localhost:11434/api"
    ollama_model: str = "gemma3:latest"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cli_api_base_url: str = "http://127.0.0.1:8000"
    cli_state_path: str = ".local/a-new-dawn-session.json"

    @property
    def cli_state_file(self) -> Path:
        return Path(self.cli_state_path)

    @property
    def resolved_supabase_jwks_url(self) -> str:
        return self.supabase_jwks_url or f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def resolved_supabase_jwt_issuer(self) -> str:
        return self.supabase_jwt_issuer or f"{self.supabase_url}/auth/v1"

    @property
    def resolved_publishable_key(self) -> str:
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def llm_base_url(self) -> str | None:
        provider = self.llm_provider.lower()
        if provider == "modelrelay":
            return self.modelrelay_base_url
        if provider == "ollama":
            return self.ollama_base_url
        if provider == "gemini":
            return self.gemini_base_url
        return self.openai_base_url

    @property
    def llm_api_key(self) -> str | None:
        provider = self.llm_provider.lower()
        if provider == "modelrelay":
            return self.modelrelay_api_key
        if provider == "ollama":
            return "ollama"
        if provider == "gemini":
            return self.gemini_api_key
        return self.openai_api_key

    @property
    def llm_model(self) -> str:
        provider = self.llm_provider.lower()
        if provider == "modelrelay":
            return self.modelrelay_model
        if provider == "ollama":
            return self.ollama_model
        if provider == "gemini":
            return self.gemini_model
        return self.openai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
