from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Fuente única de verdad para la configuración del proyecto.

    Compartida por el pipeline ETL (`etl/`) y la aplicación (`src/`).
    Carga valores desde variables de entorno y el archivo `.env`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── ETL / scraping ──
    api_base_url: str = "https://apisae.mineduc.cl"
    comunas_api_url: str = "https://api.baseapi.cl/api/v1/sii/datos/comunas"
    max_concurrent_requests: int = 5
    request_delay_seconds: float = 1.0
    max_retries: int = 5
    request_timeout: int = 30
    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")
    logs_dir: Path = Path("logs")
    state_file: Path = Path("data/state.json")
    log_level: str = "INFO"
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # ── Backend / persistencia ──
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://colegios:colegios@localhost:5432/colegios"
    api_port: int = 8000
    frontend_port: int = 4321
    cors_origins: str = ""

    @property
    def comunas_raw_dir(self) -> Path:
        return self.raw_dir / "comunas"

    @property
    def establecimientos_raw_dir(self) -> Path:
        return self.raw_dir / "establecimientos"

    @property
    def comunas_mapeo_file(self) -> Path:
        return Path("assets/comunas_mapeo.json")

    @property
    def latest_processed_dir(self) -> Path:
        return self.processed_dir / "latest"


settings = Settings()
