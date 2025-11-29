# =============================================================================
# Worker Service - Configuration
# =============================================================================
"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables with sensible defaults
for local development.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        gcp_project_id: Google Cloud project identifier
        gcp_region: GCP region for services
        processing_delay_per_char: Seconds to sleep per character (simulates heavy work)
        environment: Current environment (development/staging/production)
        log_level: Logging verbosity level
        service_name: Name of this service for logging/tracing
    """
    
    # Google Cloud Configuration
    gcp_project_id: str = "memory-machines-dev"
    gcp_region: str = "us-central1"
    
    # Processing Configuration
    processing_delay_per_char: float = 0.05  # 0.05s per character
    
    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"
    service_name: str = "worker"
    
    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses LRU cache to avoid re-reading environment variables
    on every request.
    
    Returns:
        Settings: Application configuration instance
    """
    return Settings()
