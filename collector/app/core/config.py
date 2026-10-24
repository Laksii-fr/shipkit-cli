"""Collector settings, from the environment.

    SHIPKIT_COLLECTOR_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHIPKIT_COLLECTOR_")

    database_url: str = "postgresql+psycopg://shipkit:shipkit@localhost:5432/shipkit"
    app_name: str = "ShipKit Collector"
