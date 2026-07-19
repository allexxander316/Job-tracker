from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")

    hh_access_token: str = Field(alias="HH_API_ACCESS_TOKEN")
    hh_base_url: str = "https://api.hh.ru/vacancies"
    hh_professional_role: int = 96
    hh_search_text: str = "python"
    database_url: str = Field(alias="DATABASE_URL")
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")


settings = Settings()
