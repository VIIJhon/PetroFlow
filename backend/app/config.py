"""
PetroFlow Configuration
Application settings and environment variables
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "PetroFlow"
    VERSION: str = "3.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # Database (default to local SQLite for development)
    DATABASE_URL: str = "sqlite:///petroflow.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_ENABLED: bool = True
    
    # MQTT
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_TOPIC_PREFIX: str = "petroflow"
    MQTT_QOS: int = 1
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".json", ".pdf"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/petroflow.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Security
    BCRYPT_ROUNDS: int = 12
    PASSWORD_MIN_LENGTH: int = 8
    MFA_ENABLED: bool = True
    SESSION_TIMEOUT: int = 3600  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Email (for notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Feature Flags
    ENABLE_AI_DIAGNOSTICS: bool = True
    ENABLE_3D_VIEWER: bool = True
    ENABLE_REAL_TIME_SIMULATION: bool = True
    ENABLE_PREDICTIVE_MAINTENANCE: bool = True
    
    # Google Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-pro"
    GEMINI_RATE_LIMIT_PER_MINUTE: int = 15  # Free tier limit
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_TIMEOUT: int = 30  # seconds
    
    # Google OAuth 2.0
    # Authored by Jhon Villegas
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_OAUTH_SCOPES: List[str] = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    # Frontend URL for OAuth redirects
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Simulation Settings
    SIMULATION_MAX_ITERATIONS: int = 1000
    SIMULATION_CONVERGENCE_TOLERANCE: float = 1e-6
    SIMULATION_TIMEOUT: int = 300  # 5 minutes
    
    # Analysis Settings
    ANALYSIS_CACHE_ENABLED: bool = True
    ANALYSIS_PARALLEL_WORKERS: int = 4
    ANALYSIS_MAX_DATA_POINTS: int = 100000
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100
    WS_MESSAGE_QUEUE_SIZE: int = 1000
    
    class Config:
        # Load .env from the project root (two levels up from this file)
        from pathlib import Path
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()


# Database URL for SQLAlchemy (sync)
def get_database_url() -> str:
    """Get database URL for SQLAlchemy"""
    return settings.DATABASE_URL


# Async database URL
def get_async_database_url() -> str:
    """Get async database URL for SQLAlchemy"""
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


# Redis configuration
def get_redis_config() -> dict:
    """Get Redis configuration"""
    return {
        "url": settings.REDIS_URL,
        "encoding": "utf-8",
        "decode_responses": True
    }


# MQTT configuration
def get_mqtt_config() -> dict:
    """Get MQTT configuration"""
    return {
        "broker": settings.MQTT_BROKER,
        "port": settings.MQTT_PORT,
        "username": settings.MQTT_USERNAME,
        "password": settings.MQTT_PASSWORD,
        "topic_prefix": settings.MQTT_TOPIC_PREFIX,
        "qos": settings.MQTT_QOS
    }


# Logging configuration
def get_logging_config() -> dict:
    """Get logging configuration"""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "default",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "detailed",
                "filename": settings.LOG_FILE,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT
            }
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console", "file"]
        }
    }