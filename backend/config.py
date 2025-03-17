import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # API Keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # File storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    GENERATED_REPORTS_DIR: str = os.getenv("GENERATED_REPORTS_DIR", "./generated_reports")
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
