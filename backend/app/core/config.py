import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Portfolio Project Reviewer"
    API_PREFIX: str = "/api"
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/portfolio_reviewer.db"
    DATA_DIR: str = str(ROOT_DIR / "data")
    SCRATCH_DIR: str = str(ROOT_DIR / "data" / "scratch")
    SAMPLE_PROJECTS_DIR: str = str(ROOT_DIR / "sample_projects")
    
    # Sandboxing & Safety Limits
    MAX_REPO_SIZE_MB: int = 25
    MAX_REPO_FILES: int = 500
    MAX_FILE_SIZE_KB: int = 500
    
    # AI Engine
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # CORS — explicit local development origins only; no wildcard
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.SCRATCH_DIR, exist_ok=True)
os.makedirs(settings.SAMPLE_PROJECTS_DIR, exist_ok=True)

