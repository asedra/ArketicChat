"""
Core configuration for ATTILA AI Enhanced Function Management System
"""
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "ATTILA AI Enhanced Function Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./data/attila.db", env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=5, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis (optional)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI Services
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # OpenAI Configuration
    OPENAI_MODEL: str = Field(default="gpt-4", env="OPENAI_MODEL")
    OPENAI_TEMPERATURE: float = Field(default=0.3, env="OPENAI_TEMPERATURE")
    OPENAI_MAX_TOKENS: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    
    # Function Router Configuration
    ROUTER_MIN_CONFIDENCE: float = Field(default=0.7, env="ROUTER_MIN_CONFIDENCE")
    ROUTER_AUTO_EXECUTE_THRESHOLD: float = Field(default=0.95, env="ROUTER_AUTO_EXECUTE_THRESHOLD")
    ROUTER_MAX_FUNCTIONS: int = Field(default=5, env="ROUTER_MAX_FUNCTIONS")
    
    # Performance Targets
    MAX_EXECUTION_TIME: float = Field(default=30.0, env="MAX_EXECUTION_TIME")
    TARGET_EXECUTION_TIME: float = Field(default=2.0, env="TARGET_EXECUTION_TIME")
    MAX_MEMORY_USAGE: int = Field(default=1024, env="MAX_MEMORY_USAGE")  # MB
    
    # HTTP Client Configuration
    HTTP_TIMEOUT: int = Field(default=30, env="HTTP_TIMEOUT")
    HTTP_MAX_RETRIES: int = Field(default=3, env="HTTP_MAX_RETRIES")
    HTTP_RETRY_BACKOFF: float = Field(default=2.0, env="HTTP_RETRY_BACKOFF")
    
    # WebSocket Configuration
    WS_CONNECTION_TIMEOUT: int = Field(default=30, env="WS_CONNECTION_TIMEOUT")
    WS_MAX_CONNECTIONS: int = Field(default=100, env="WS_MAX_CONNECTIONS")
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=8001, env="METRICS_PORT")
    
    # Background Tasks
    CELERY_BROKER_URL: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")
    
    # Function Types Configuration
    ENABLED_FUNCTION_TYPES: List[str] = Field(
        default=["basic", "api", "prompt", "document", "mcp"], 
        env="ENABLED_FUNCTION_TYPES"
    )
    
    # Document Processing
    DOCUMENT_CHUNK_SIZE: int = Field(default=1000, env="DOCUMENT_CHUNK_SIZE")
    DOCUMENT_OVERLAP: int = Field(default=200, env="DOCUMENT_OVERLAP")
    EMBEDDING_MODEL: str = Field(default="text-embedding-ada-002", env="EMBEDDING_MODEL")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Development
    AUTO_RELOAD: bool = Field(default=False, env="AUTO_RELOAD")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @validator("ENABLED_FUNCTION_TYPES", pre=True)
    def parse_function_types(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
        
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
        
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL"""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return not self.DEBUG
        
    @property
    def function_type_config(self) -> Dict[str, Dict[str, Any]]:
        """Get function type specific configuration"""
        return {
            "basic": {
                "timeout": 30,
                "max_retries": 3,
                "memory_limit": 256
            },
            "api": {
                "timeout": self.HTTP_TIMEOUT,
                "max_retries": self.HTTP_MAX_RETRIES,
                "memory_limit": 512
            },
            "prompt": {
                "timeout": 60,
                "max_retries": 2,
                "memory_limit": 1024,
                "model": self.OPENAI_MODEL,
                "temperature": self.OPENAI_TEMPERATURE,
                "max_tokens": self.OPENAI_MAX_TOKENS
            },
            "document": {
                "timeout": 120,
                "max_retries": 2,
                "memory_limit": 2048,
                "chunk_size": self.DOCUMENT_CHUNK_SIZE,
                "overlap": self.DOCUMENT_OVERLAP,
                "embedding_model": self.EMBEDDING_MODEL
            },
            "mcp": {
                "timeout": self.WS_CONNECTION_TIMEOUT,
                "max_retries": 5,
                "memory_limit": 512,
                "heartbeat_interval": self.WS_HEARTBEAT_INTERVAL
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()