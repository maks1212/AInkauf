from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AInkauf API"
    database_url: str = Field(
        default="postgresql+psycopg://ainkauf:ainkauf@localhost:5432/ainkauf"
    )
    google_maps_api_key: str | None = None
    default_fuel_price_diesel: float = 1.62
    default_fuel_price_benzin: float = 1.69
    default_fuel_price_autogas: float = 0.95
    default_energy_price_strom: float = 0.35
    default_transit_cost_per_km: float = 0.40


@lru_cache
def get_settings() -> Settings:
    return Settings()
