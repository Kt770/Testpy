from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost/contract_mgmt")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # AI/OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4"
    
    # DocuSign
    DOCUSIGN_CLIENT_ID: str = os.getenv("DOCUSIGN_CLIENT_ID", "")
    DOCUSIGN_CLIENT_SECRET: str = os.getenv("DOCUSIGN_CLIENT_SECRET", "")
    DOCUSIGN_BASE_URL: str = "https://demo.docusign.net/restapi"
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Redis/Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Saudi Cloud specific
    SAUDI_CLOUD_REGION: str = os.getenv("SAUDI_CLOUD_REGION", "riyadh")
    SAUDI_CLOUD_ENDPOINT: str = os.getenv("SAUDI_CLOUD_ENDPOINT", "")
    
    class Config:
        env_file = ".env"

settings = Settings()