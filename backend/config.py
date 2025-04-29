import os

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback to pydantic BaseSettings if pydantic_settings is not available
    from pydantic import BaseSettings
import logging
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic import Field, validator

# Load environment variables from .env file
load_dotenv()

# Use absolute paths for uploads and generated reports
# If running on Render with backend as root, we need to adjust paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set up logger directly instead of importing from error_handler to avoid circular imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if we're in production mode
IS_PRODUCTION = os.getenv("NODE_ENV") == "production"


# Helper function to determine appropriate data directories for the environment
def get_data_dirs():
    """
    Get appropriate data directories based on environment (dev, prod, Render, etc.)
    Returns tuple of (uploads_dir, reports_dir)
    """
    # For Render with persistent disk
    if IS_PRODUCTION and os.path.exists("/var/data"):
        uploads_dir = "/var/data/uploads"
        reports_dir = "/var/data/generated_reports"
        logger.info("Using Render persistent disk for storage")
    else:
        # For local development or if persistent disk isn't available
        uploads_dir = os.getenv(
            "UPLOAD_DIR", os.path.join(os.path.dirname(BASE_DIR), "uploads")
        )
        reports_dir = os.getenv(
            "GENERATED_REPORTS_DIR",
            os.path.join(os.path.dirname(BASE_DIR), "generated_reports"),
        )

    return uploads_dir, reports_dir


# Get appropriate data directories
UPLOADS_DIR, REPORTS_DIR = get_data_dirs()


class Settings(BaseSettings):
    """Application settings."""

    # Base configuration
    APP_NAME: str = "Insurance Report Generator"
    DEBUG: bool = False
    BASE_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = Field(
        default=os.getenv("NODE_ENV", "development"),
        description="Current environment (development/production)"
    )

    # Supabase configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Share link configuration
    DEFAULT_SHARE_LINK_EXPIRY: int = 86400  # 24 hours
    MAX_SHARE_LINK_EXPIRY: int = 2592000  # 30 days
    MIN_SHARE_LINK_EXPIRY: int = 300  # 5 minutes
    DEFAULT_MAX_DOWNLOADS: int = 1
    MAX_DOWNLOADS_LIMIT: int = 100

    # API Keys
    OPENROUTER_API_KEY: str = Field(
        default=os.getenv("OPENROUTER_API_KEY", ""),
        description="OpenRouter API key for AI model access",
    )

    # OpenRouter API settings
    OPENROUTER_API_ENDPOINT: str = Field(
        default=os.getenv(
            "OPENROUTER_API_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"
        ),
        description="OpenRouter API endpoint URL",
    )
    APP_DOMAIN: str = Field(
        # Use FRONTEND_URL if APP_DOMAIN is not set explicitly
        default=os.getenv(
            "APP_DOMAIN",
            os.getenv(
                "FRONTEND_URL", "https://insurance-report-generator.vercel.app"
            ).rstrip("/"),
        ),
        description="Application domain for API referrer headers",
    )

    # Important: We are no longer using direct DATABASE_URL connections
    # All database operations should use the Supabase client
    # DATABASE_URL is kept for backwards compatibility only and should be removed
    # in future versions
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # File storage - use appropriate paths
    UPLOAD_DIR: str = Field(
        default=UPLOADS_DIR, description="Directory for uploaded files"
    )
    GENERATED_REPORTS_DIR: str = Field(
        default=REPORTS_DIR, description="Directory for generated report files"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=int(os.getenv("MAX_UPLOAD_SIZE", "1073741824")),
        description="Maximum upload size in bytes (1GB default)",
    )

    # Data retention settings - how long to keep files before auto-deletion
    DATA_RETENTION_HOURS: int = int(
        os.getenv("DATA_RETENTION_HOURS", "2")
    )  # Default to 2 hours

    # API Settings
    API_RATE_LIMIT: int = int(os.getenv("API_RATE_LIMIT", "100"))  # Requests per hour
    NEXT_PUBLIC_API_URL: str = os.getenv(
        "NEXT_PUBLIC_API_URL", "https://report-gen-5wtl.onrender.com"
    )

    # AI Model Settings
    DEFAULT_MODEL: str = os.getenv(
        "DEFAULT_MODEL", "google/gemini-2.0-pro-exp-02-05:free"
    )

    # Token limit
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "16000"))

    # CORS Settings
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://report-gen-liard.vercel.app")
    CORS_ALLOW_ALL: bool = Field(
        default=os.getenv("CORS_ALLOW_ALL", "").lower() in ("true", "1", "yes"),
        description="Whether to allow all origins for CORS"
    )

    # Additional allowed origins beyond the FRONTEND_URL
    ADDITIONAL_ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "https://report-gen-liard.vercel.app",  # Vercel frontend
            "https://report-gen-5wtl.onrender.com",  # Render backend
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Additional allowed origins for CORS",
    )

    # File processing settings
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".docx", ".doc", ".txt", 
        ".jpg", ".jpeg", ".png"
    ]
    MAX_TOTAL_SIZE: int = 104857600  # 100MB
    INDIVIDUAL_FILE_SIZE_RATIO: float = 0.8  # Individual file size limit as ratio of total
    CHUNK_SIZE: int = 8192  # 8KB chunks for file processing
    
    @property
    def MAX_INDIVIDUAL_FILE_SIZE(self) -> int:
        return int(self.MAX_TOTAL_SIZE * self.INDIVIDUAL_FILE_SIZE_RATIO)

    # All allowed origins combining FRONTEND_URL and ADDITIONAL_ALLOWED_ORIGINS
    @property
    def allowed_origins(self) -> List[str]:
        """Get all allowed origins for CORS configuration"""
        # Ensure both production URLs are always included
        required_origins = [
            "https://report-gen-liard.vercel.app",  # Vercel frontend
            "https://report-gen-5wtl.onrender.com",  # Render backend
        ]

        if os.getenv("CORS_ALLOW_ALL", "").lower() in ("true", "1", "yes"):
            return ["*"]

        # Get frontend URLs as a list
        frontend_urls = (
            self.FRONTEND_URL
            if isinstance(self.FRONTEND_URL, list)
            else [self.FRONTEND_URL]
        )

        # Combine and deduplicate URLs, ensuring required origins are included
        all_origins = list(
            set(frontend_urls + self.ADDITIONAL_ALLOWED_ORIGINS + required_origins)
        )

        # Log the allowed origins in development
        if not IS_PRODUCTION:
            logger.info(f"CORS allowed origins: {all_origins}")

        return all_origins

    # Validators for critical settings
    @validator("OPENROUTER_API_KEY")
    def validate_openrouter_api_key(cls, v):
        if not v or len(v) < 10:
            logger.warning("OPENROUTER_API_KEY is missing or appears to be invalid")
        return v

    @validator("SUPABASE_URL")
    def validate_supabase_url(cls, v):
        if not v or not v.startswith("https://"):
            logger.warning(
                "SUPABASE_URL is missing or invalid (should start with https://)"
            )
        return v

    @validator("SUPABASE_KEY")
    def validate_supabase_key(cls, v):
        if not v or len(v) < 10:
            logger.warning("SUPABASE_KEY is missing or appears to be invalid")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env without validation errors

    def validate_all(self) -> List[str]:
        """
        Validate all required environment variables and return a list of missing ones.

        Returns:
            List of names of missing or invalid environment variables
        """
        missing = []

        # Check key API requirements
        if not self.OPENROUTER_API_KEY or len(self.OPENROUTER_API_KEY) < 10:
            missing.append("OPENROUTER_API_KEY")

        # Check Supabase requirements if using Supabase
        if (self.SUPABASE_URL and not self.SUPABASE_KEY) or (
            not self.SUPABASE_URL and self.SUPABASE_KEY
        ):
            # If one is provided but not the other
            missing.append("SUPABASE_URL and SUPABASE_KEY (both must be provided)")

        # Check frontend URL for CORS
        if not self.FRONTEND_URL:
            missing.append("FRONTEND_URL")

        return missing


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, using environment variables and defaults.
    The result is cached to avoid reading the environment each time.

    Returns:
        Settings instance
    """
    return Settings()


# Create settings instance
settings = get_settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)

# Validate settings
missing_vars = settings.validate_all()
if missing_vars:
    logger.warning(
        f"Missing or invalid required environment variables: {', '.join(missing_vars)}"
    )
    logger.warning(
        "The application may not function correctly without these variables."
    )

print(
    f"Config loaded. Upload dir: {settings.UPLOAD_DIR}, Generated reports dir: {settings.GENERATED_REPORTS_DIR}"
)
print(f"Data retention period: {settings.DATA_RETENTION_HOURS} hours")

# Test user credentials for testing (not for production use)
TEST_USER = {
    "email": "test@example.com",
    "password": "test_password123"
}
