from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "RoadSoS API"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://roadsos:roadsos@localhost:5432/roadsos"
    database_url_sync: str = "postgresql://roadsos:roadsos@localhost:5432/roadsos"

    @property
    def async_database_url(self) -> str:
        """Ensure the URL uses asyncpg driver (Railway provides postgresql://)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_number: Optional[str] = None
    twilio_sms_number: Optional[str] = None

    whatsapp_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_verify_token: str = "roadsos_verify_2026"

    opencage_api_key: Optional[str] = None
    mapbox_token: Optional[str] = None

    llm_model_path: str = "meta-llama/Llama-3.1-8B-Instruct"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    triage_confidence_threshold: float = 0.78
    max_triage_questions: int = 5

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    data_retention_hours: int = 24
    health_data_retention_days: int = 30

    osm_routing_url: str = "http://localhost:5000"
    use_mock_llm: bool = True
    use_mock_dispatch: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
