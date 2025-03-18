import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

# Use absolute paths for uploads and generated reports
# If running on Render with backend as root, we need to adjust paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    # API Keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # File storage - use absolute paths
    UPLOAD_DIR: str = os.path.abspath(os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(BASE_DIR), "uploads")))
    GENERATED_REPORTS_DIR: str = os.path.abspath(os.getenv("GENERATED_REPORTS_DIR", os.path.join(os.path.dirname(BASE_DIR), "generated_reports")))
    MAX_UPLOAD_SIZE: int = int(
        os.getenv("MAX_UPLOAD_SIZE", "104857600")
    )  # 100MB default

    # API Settings
    API_RATE_LIMIT: int = int(
        os.getenv("API_RATE_LIMIT", "100")
    )  # Requests per hour
    NEXT_PUBLIC_API_URL: str = os.getenv("NEXT_PUBLIC_API_URL", "")

    # AI Model Settings
    DEFAULT_MODEL: str = os.getenv(
        "DEFAULT_MODEL", "google/gemini-2.0-pro-exp-02-05:free"
    )
    
    # Token limit
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "16000"))
    
    # CORS Settings
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env without validation errors


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)

print(f"Config loaded. Upload dir: {settings.UPLOAD_DIR}, Generated reports dir: {settings.GENERATED_REPORTS_DIR}")
