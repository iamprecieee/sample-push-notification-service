from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    push_queue_name: str = "push_notifications"
    failed_queue_name: str = "failed_notifications"
    prefetch_count: int = 10

    redis_url: str = "redis://localhost:6379/0"
    idempotency_ttl_seconds: int = 3600

    database_url: str = "postgresql://postgres:postgres@localhost:5432/notifications_db"

    fcm_project_id: str
    google_application_credentials: str = "./service-account.json"

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    circuit_breaker_success_threshold: int = 3

    max_retry_attempts: int = 5
    initial_retry_delay_ms: int = 100
    max_retry_delay_ms: int = 5000
    retry_backoff_multiplier: int = 2

    worker_concurrency: int = 4

    server_port: int = 8080

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()