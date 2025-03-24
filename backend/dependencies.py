from fastapi import Depends
from typing import AsyncGenerator
from .services.document_service import DocumentService
from .config import get_settings

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
    return get_settings() 