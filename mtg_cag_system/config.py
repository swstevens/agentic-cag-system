from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application configuration"""

    # API Settings
    app_name: str = "MTG CAG System"
    app_version: str = "1.0.0"
    debug: bool = True

    # Model Settings
    default_model: str = "openai:gpt-4o-mini"  # Cheap model for testing
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Optional: Per-agent model configuration
    scheduling_model: Optional[str] = None  # Falls back to default_model
    knowledge_model: Optional[str] = None   # Falls back to default_model
    symbolic_model: Optional[str] = None    # Falls back to default_model

    # CAG Settings
    mtgjson_path: str = "./data/mtgjson/AllPrintings.json"
    default_format: str = "Standard"
    preload_on_startup: bool = True

    # Cache Settings
    cache_l1_max_size: int = 200
    cache_l2_max_size: int = 1000
    cache_l3_max_size: int = 10000

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
