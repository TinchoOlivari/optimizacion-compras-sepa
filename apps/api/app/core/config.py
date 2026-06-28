from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://tfg:tfg@db:5432/tfg"
    api_base_url: str = "http://localhost:8000"
    auth_url: str = "http://localhost:3000"
    osrm_url: str = "http://osrm:5000"
    default_max_paradas: int = 3
    default_preferencia: str = "MENOR_PRECIO"
    api_jwt_secret: str = "cambiar-en-produccion"
    jwt_expiration_minutes: int = 525600
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@tfg.local"
    reset_token_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
