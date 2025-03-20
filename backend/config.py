import os
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from dotenv import load_dotenv
import sys
from typing import List

# Load environment variables from .env file
load_dotenv()

# Use absolute paths for uploads and generated reports
# If running on Render with backend as root, we need to adjust paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Import logger
try:
    from utils.error_handler import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # API Keys
    OPENROUTER_API_KEY: str = Field(
        default=os.getenv("OPENROUTER_API_KEY", ""), 
        description="OpenRouter API key for AI model access"
    )
    
    # OpenRouter API settings
    OPENROUTER_API_ENDPOINT: str = Field(
        default=os.getenv("OPENROUTER_API_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
        description="OpenRouter API endpoint URL"
    )
    APP_NAME: str = Field(
        default=os.getenv("APP_NAME", "Insurance Report Generator"),
        description="Application name for API headers"
    )
    APP_DOMAIN: str = Field(
        # Use FRONTEND_URL if APP_DOMAIN is not set explicitly
        default=os.getenv("APP_DOMAIN", os.getenv("FRONTEND_URL", "https://insurance-report-generator.vercel.app").rstrip('/')),
        description="Application domain for API referrer headers"
    )

    # Supabase - Primary database and storage solution
    SUPABASE_URL: str = Field(
        default=os.getenv("SUPABASE_URL", ""), 
        description="Supabase project URL"
    )
    SUPABASE_KEY: str = Field(
        default=os.getenv("SUPABASE_KEY", ""), 
        description="Supabase API key"
    )

    # Important: We are no longer using direct DATABASE_URL connections
    # All database operations should use the Supabase client
    # DATABASE_URL is kept for backwards compatibility only and should be removed
    # in future versions
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # File storage - use absolute paths
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(BASE_DIR), "uploads"))
    GENERATED_REPORTS_DIR: str = os.getenv("GENERATED_REPORTS_DIR", os.path.join(os.path.dirname(BASE_DIR), "generated_reports"))
    MAX_UPLOAD_SIZE: int = int(
        os.getenv("MAX_UPLOAD_SIZE", "1073741824")
    )  # 1GB default

    # Data retention settings - how long to keep files before auto-deletion
    DATA_RETENTION_HOURS: int = int(
        os.getenv("DATA_RETENTION_HOURS", "2")
    )  # Default to 2 hours
    
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
    
    # Parse allowed origins from environment
    @validator('FRONTEND_URL')
    def parse_frontend_url(cls, v):
        if not v:
            logger.warning("FRONTEND_URL is missing")
            return ["http://localhost:3000"]
        
        # Split by comma if it's a comma-separated list
        urls = v.split(',') if ',' in v else [v]
        
        # Add common local development URLs if they're not already included
        common_local_urls = ["http://localhost:3000", "http://127.0.0.1:3000"]
        for local_url in common_local_urls:
            if local_url not in urls:
                urls.append(local_url)
                
        return urls
    
    # Additional allowed origins beyond the FRONTEND_URL
    ADDITIONAL_ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "https://report-gen-liard.vercel.app",
            "https://report-gen.vercel.app",
            "https://report-gen-5wtl.onrender.com"
        ],
        description="Additional allowed origins for CORS"
    )
    
    # All allowed origins combining FRONTEND_URL and ADDITIONAL_ALLOWED_ORIGINS
    @property
    def allowed_origins(self) -> List[str]:
        """Get all allowed origins for CORS configuration"""
        if os.getenv("CORS_ALLOW_ALL", "").lower() in ("true", "1", "yes"):
            return ["*"]
            
        return self.FRONTEND_URL + self.ADDITIONAL_ALLOWED_ORIGINS

    # Validators for critical settings
    @validator('OPENROUTER_API_KEY')
    def validate_openrouter_api_key(cls, v):
        if not v or len(v) < 10:
            logger.warning("OPENROUTER_API_KEY is missing or appears to be invalid")
        return v
    
    @validator('SUPABASE_URL')
    def validate_supabase_url(cls, v):
        if not v or not v.startswith('https://'):
            logger.warning("SUPABASE_URL is missing or invalid (should start with https://)")
        return v
    
    @validator('SUPABASE_KEY')
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
        if (self.SUPABASE_URL and not self.SUPABASE_KEY) or (not self.SUPABASE_URL and self.SUPABASE_KEY):
            # If one is provided but not the other
            missing.append("SUPABASE_URL and SUPABASE_KEY (both must be provided)")
            
        # Check frontend URL for CORS
        if not self.FRONTEND_URL:
            missing.append("FRONTEND_URL")
            
        return missing


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)

# Validate settings
missing_vars = settings.validate_all()
if missing_vars:
    logger.warning(f"Missing or invalid required environment variables: {', '.join(missing_vars)}")
    logger.warning("The application may not function correctly without these variables.")

print(f"Config loaded. Upload dir: {settings.UPLOAD_DIR}, Generated reports dir: {settings.GENERATED_REPORTS_DIR}")
print(f"Data retention period: {settings.DATA_RETENTION_HOURS} hours")
