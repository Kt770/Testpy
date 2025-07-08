from pydantic import BaseSettings, validator
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./contract_management.db"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # DocuSign
    DOCUSIGN_INTEGRATION_KEY: Optional[str] = None
    DOCUSIGN_USER_ID: Optional[str] = None
    DOCUSIGN_ACCOUNT_ID: Optional[str] = None
    DOCUSIGN_BASE_PATH: str = "https://demo.docusign.net/restapi"
    DOCUSIGN_PRIVATE_KEY_PATH: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@contractmanager.com"
    
    # Application
    APP_NAME: str = "Contract Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            return v
        return "sqlite:///./contract_management.db"


settings = Settings()