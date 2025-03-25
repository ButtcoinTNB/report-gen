"""
Main application entrypoint for the Insurance Report Generator API
Handles both development and production environments
"""

# ruff: noqa: E402

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize Sentry
sentry_sdk.init(
    dsn="https://348b613d688cab3b34c8b9f6b259bd15@o4509033743646720.ingest.de.sentry.io/4509033752887376",
    # Add data like request headers and IP for users
    send_default_pii=True,
)

# Set up logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logger.info(f"Added project root to Python path: {project_root}")

# Ensure necessary directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)

# Now we can safely import everything else
from api import documents, reports, share, templates
from api.upload_chunked import router as upload_chunked_router
from config import settings
from fastapi.staticfiles import StaticFiles

# Import our custom middleware and monitoring
from middleware.error_handler import error_handler_middleware
from middleware.rate_limiter import rate_limit_middleware

# Import utilities
from utils.file_utils import safe_path_join
from utils.metrics import MetricsCollector, initialize
from utils.supabase_helper import (
    cleanup_expired_connections,
    async_supabase_client_context,
)
from utils.api_rate_limiter import ApiRateLimiter

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)
logger.info(
    f"Ensured directories exist: {settings.UPLOAD_DIR}, {settings.GENERATED_REPORTS_DIR}"
)

# Validate environment variables
missing_vars = settings.validate_all()
if missing_vars:
    logger.warning(
        f"⚠️ STARTUP WARNING: Missing or invalid environment variables: {', '.join(missing_vars)}"
    )
    logger.warning(
        "⚠️ Some application features may not work correctly. Please check your .env file."
    )
else:
    logger.info("✅ All required environment variables are properly configured.")


# Define lifespan to handle startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application lifecycle
    """
    # Initialize task variables
    supabase_cleanup_task = None
    rate_limiter_cleanup_task = None

    # Startup - run initialization
    logger.info("Starting application...")

    # Initialize monitoring
    try:
        logger.info("Initializing monitoring...")
        initialize()
    except Exception as e:
        logger.error(f"Error initializing monitoring: {e}")

    # Initialize rate limiter
    try:
        logger.info("Initializing API rate limiter...")
        await ApiRateLimiter.get_instance().start()
    except Exception as e:
        logger.error(f"Error initializing API rate limiter: {e}")

    # Create background tasks
    try:
        logger.info("Creating background cleanup tasks...")

        # Task for cleaning up the Supabase connections
        supabase_cleanup_task = asyncio.create_task(
            start_supabase_connection_cleanup_scheduler()
        )

        # Task for cleaning up the rate limiter and resetting metrics
        rate_limiter_cleanup_task = asyncio.create_task(
            start_rate_limiter_cleanup_scheduler()
        )
    except Exception as e:
        logger.error(f"Error creating background tasks: {e}")

    yield

    # Shutdown - cleanup resources
    logger.info("Shutting down application...")

    # Stop the rate limiter
    try:
        logger.info("Stopping API rate limiter...")
        await ApiRateLimiter.get_instance().stop()
    except Exception as e:
        logger.error(f"Error stopping API rate limiter: {e}")

    # Cancel cleanup tasks
    try:
        logger.info("Canceling background tasks...")
        if "supabase_cleanup_task" in locals() and supabase_cleanup_task:
            supabase_cleanup_task.cancel()

        if "rate_limiter_cleanup_task" in locals() and rate_limiter_cleanup_task:
            rate_limiter_cleanup_task.cancel()
    except Exception as e:
        logger.error(f"Error canceling background tasks: {e}")


# Create FastAPI app with lifespan manager
app = FastAPI(
    title="Insurance Report Generator API",
    description="API for the Insurance Report Generator",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware first
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add our custom middleware
app.middleware("http")(error_handler_middleware)
app.middleware("http")(rate_limit_middleware)

# Remove the old exception handlers as they're now handled by error_handler_middleware
# ... remove existing exception handlers ...

# Keep the existing cleanup functions
# ... keep existing cleanup_old_data and start_cleanup_scheduler ...

# Keep the existing root and health check endpoints
# ... keep existing endpoints ...

# Import and include routers
from api import tasks

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(share.router, prefix="/api/share", tags=["share"])
app.include_router(
    upload_chunked_router, prefix="/api/upload-chunked", tags=["uploads"]
)

# Serve static files
upload_dir = Path("./uploads")
upload_dir.mkdir(exist_ok=True)
app.mount("/files", StaticFiles(directory="./uploads"), name="files")

# Add temp directory for processing files
temp_dir = Path("./temp_files")
temp_dir.mkdir(exist_ok=True)

# Initialize metrics collector
metrics_collector = MetricsCollector(
    metrics_file=Path(project_root) / "data" / "metrics.json",
)


# Add a function to clean up old reports and uploads
async def cleanup_old_data(max_age_hours: int = 24):
    """
    Clean up old reports and uploads that haven't been accessed in the specified time.
    """
    try:
        logger.info(
            f"Starting cleanup of abandoned data older than {max_age_hours} hours"
        )
        current_time = time.time()
        files_cleaned = 0

        # Clean up old uploads
        if os.path.exists(settings.UPLOAD_DIR):
            for item in os.listdir(settings.UPLOAD_DIR):
                try:
                    item_path = safe_path_join(settings.UPLOAD_DIR, item)
                    if not os.path.isdir(item_path):
                        continue

                    # Check directory age and clean if old
                    latest_mod_time = max(
                        os.path.getmtime(os.path.join(root, file))
                        for root, _, files in os.walk(item_path)
                        for file in files
                    )

                    age_hours = (current_time - latest_mod_time) / 3600
                    if age_hours > max_age_hours:
                        for root, _, files in os.walk(item_path, topdown=False):
                            for file in files:
                                try:
                                    file_path = safe_path_join(root, file)
                                    os.remove(file_path)
                                    files_cleaned += 1
                                except Exception as e:
                                    logger.error(
                                        f"Error deleting file {file}: {str(e)}"
                                    )

                        try:
                            os.rmdir(item_path)
                            logger.info(f"Cleaned up old upload directory: {item_path}")
                        except Exception as e:
                            logger.error(
                                f"Error removing directory {item_path}: {str(e)}"
                            )

                except Exception as e:
                    logger.error(f"Error processing upload directory {item}: {str(e)}")

        # Clean up old generated reports
        if os.path.exists(settings.GENERATED_REPORTS_DIR):
            for file in os.listdir(settings.GENERATED_REPORTS_DIR):
                try:
                    file_path = safe_path_join(settings.GENERATED_REPORTS_DIR, file)
                    if not os.path.isfile(file_path):
                        continue

                    age_hours = (current_time - os.path.getmtime(file_path)) / 3600
                    if age_hours > max_age_hours:
                        os.remove(file_path)
                        files_cleaned += 1
                        logger.info(f"Cleaned up old generated file: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {file}: {str(e)}")

        # Clean up preview files
        try:
            from services.preview_service import preview_service

            preview_service.cleanup_old_previews(max_age_hours)
        except Exception as e:
            logger.error(f"Error cleaning up previews: {str(e)}")

        # Update database for cleaned files
        try:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                max_age_time = datetime.now() - timedelta(hours=max_age_hours)

                # First, check if the files_cleaned column exists
                try:
                    async with async_supabase_client_context() as supabase:
                        # Try to get a single row to check schema
                        response = (
                            await supabase.table("reports")
                            .select("*")
                            .limit(1)
                            .execute()
                        )
                        if response.data and "files_cleaned" in response.data[0]:
                            # Column exists, proceed with update
                            # Update records where files_cleaned is null and created_at is older than max_age_time
                            response = await (
                                supabase.table("reports")
                                .update({"files_cleaned": True})
                                .filter("created_at", "lt", max_age_time.isoformat())
                                .filter("files_cleaned", "is", "null")
                                .execute()
                            )

                            logger.info(
                                f"Updated database for cleaned files: {response}"
                            )
                        else:
                            logger.info(
                                "Skipping database update: files_cleaned column not found in schema"
                            )
                except Exception as schema_error:
                    logger.warning(
                        f"Error checking schema, skipping database update: {str(schema_error)}"
                    )

        except Exception as e:
            logger.error(f"Error updating database: {str(e)}")

        logger.info(f"Cleanup complete. Removed {files_cleaned} stale files.")

    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {str(e)}")


# Configure background task for periodic cleanup
async def start_cleanup_scheduler():
    """Start a background task that runs the cleanup function every hour"""
    while True:
        await cleanup_old_data(settings.DATA_RETENTION_HOURS)
        await asyncio.sleep(3600)  # Wait for 1 hour


# Configure background task for periodic Supabase connection cleanup
async def start_supabase_connection_cleanup_scheduler():
    """Start a background task that cleans up stale Supabase connections"""
    while True:
        try:
            removed = cleanup_expired_connections()
            if removed > 0:
                logger.info(f"Cleaned up {removed} expired Supabase connections")
        except Exception as e:
            logger.error(f"Error in Supabase connection cleanup: {str(e)}")

        await asyncio.sleep(300)  # Run every 5 minutes


# Configure background task for rate limiter cleanup
async def start_rate_limiter_cleanup_scheduler():
    """Start a background task that cleans up stale rate limiters and resets metrics"""
    while True:
        try:
            # Cleanup stale limiters
            ApiRateLimiter.get_instance().cleanup_stale_limiters(
                max_age_seconds=3600
            )  # 1 hour

            # Reset metrics once a day (at midnight)
            current_hour = datetime.now().hour
            if (
                current_hour == 0 and datetime.now().minute < 5
            ):  # First 5 minutes of the day
                ApiRateLimiter.get_instance().reset_metrics()
                logger.info("Daily rate limiter metrics reset completed")
        except Exception as e:
            logger.error(f"Error in rate limiter cleanup: {str(e)}")

        await asyncio.sleep(1800)  # Run every 30 minutes


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Insurance Report Generator API",
        "version": app.version,
        "status": "operational",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": app.version,
        "timestamp": datetime.now().isoformat(),
    }


# Sentry test endpoint
@app.get("/sentry-debug")
async def trigger_error():
    """
    Test endpoint to trigger a Sentry error
    """


# For local development
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        workers=int(os.getenv("WORKERS", 1)),
    )

logger.info("Application initialized successfully!")
