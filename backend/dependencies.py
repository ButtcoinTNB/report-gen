from typing import AsyncGenerator

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings as get_app_settings
    from services.document_service import DocumentService
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from config import get_settings as get_app_settings
    from services.document_service import DocumentService


async def get_document_service() -> AsyncGenerator[DocumentService, None]:
    """
    Dependency provider for DocumentService.
    Ensures proper lifecycle management of the service.
    """
    service = DocumentService()
    try:
        yield service
    finally:
        await service.close()


def get_settings():
    """
    Dependency provider for application settings.
    """
    return get_app_settings()
