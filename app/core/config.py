"""
Application configuration using Pydantic BaseSettings
Reads environment variables from .env file
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # PostgreSQL Database
    PG_HOST: str
    PG_PORT: str
    PG_USER: str
    PG_PASSWORD: str
    PG_DATABASE: str
    
    # AWS Configuration
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    AWS_REGION: str = "us-east-1"
    
    # Azure Configuration
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_CONTAINER_NAME: str
    
    # Application Settings
    APP_TITLE: str = "Warehouse API - RESTful"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
