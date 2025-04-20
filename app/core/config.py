from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smartfin AI"
    PROJECT_DESCRIPTION: str = "AI-powered financial assistant using Gemini and MongoDB"
    PROJECT_VERSION: str = "1.0.0"
    
    # MongoDB Settings
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "sample_mflix"
    
    # Google AI Settings
    GOOGLE_API_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings() 