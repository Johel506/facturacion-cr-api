"""
Configuration management for Costa Rica Electronic Invoice API
"""
import secrets
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Project info
    PROJECT_NAME: str = "Costa Rica Electronic Invoice API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = "postgresql://user:pass@localhost/test"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 20
    
    # Rate limiting
    RATE_LIMIT_BASIC: int = 100  # requests per hour for basic plan
    RATE_LIMIT_PRO: int = 500    # requests per hour for pro plan
    RATE_LIMIT_ENTERPRISE: int = 2000  # requests per hour for enterprise plan
    
    # Ministry of Finance API
    MINISTRY_API_URL_DEV: str = "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1"
    MINISTRY_API_URL_PROD: str = "https://api.comprobanteselectronicos.go.cr/recepcion/v1"
    MINISTRY_ENVIRONMENT: str = "development"  # development or production
    MINISTRY_TIMEOUT: int = 30
    
    # Encryption
    ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    
    # File storage
    MAX_CERTIFICATE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Cache TTL (in seconds)
    CERTIFICATE_CACHE_TTL: int = 3600  # 1 hour
    CABYS_CACHE_TTL: int = 86400  # 24 hours
    XSD_CACHE_TTL: int = 86400  # 24 hours
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()