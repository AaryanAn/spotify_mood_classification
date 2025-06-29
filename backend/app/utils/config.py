"""
Configuration management for the application
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Spotify API Configuration
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://127.0.0.1:8080/callback"
    
    # Database Configuration
    database_url: str
    test_database_url: str = ""
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_password: str = ""
    redis_db: int = 0
    
    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: List[str] = ["http://127.0.0.1:8080"]
    
    # ML Configuration
    model_path: str = "./ml/models/"
    enable_model_training: bool = True
    batch_size: int = 32
    learning_rate: float = 0.001
    
    # Monitoring & Logging
    log_level: str = "INFO"
    enable_metrics: bool = True
    sentry_dsn: str = ""
    
    # Development
    debug: bool = True
    reload: bool = True
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 