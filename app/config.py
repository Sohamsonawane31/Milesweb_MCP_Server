"""Configuration for the read-only connector API."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings are read from environment variables and an optional .env file."""

    connector_api_key: str = ""
    # Development-only opaque bearer-token to client-id mappings. This mock
    # emulates the already-verified identity the MCP server forwards.
    phase2_test_tokens: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
