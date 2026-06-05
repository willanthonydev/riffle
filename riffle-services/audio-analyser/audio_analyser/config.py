from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key: str = "test"
    s3_secret_key: str = "test"
    service_version: str = "local-dev"
    temp_dir: Path | None = None
    low_confidence_threshold: float | None = None

    model_config = SettingsConfigDict(env_prefix="RIFFLE_AUDIO_ANALYSER_")

