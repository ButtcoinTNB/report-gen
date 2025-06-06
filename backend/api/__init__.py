# API routes package
"""
Insurance Report Generator API Routes
"""

from fastapi import APIRouter

from .agent_loop import (
    router as agents_router,
)  # Changed from agents.py to agent_loop.py
from .documents import router as documents_router
from .format import router as formats_router  # Changed from formats.py to format.py
from .generate import router as generate_router  # Add generate router

# Import only routers that actually exist
from .reports import router as reports_router
from .tasks import router as tasks_router
from .upload import router as uploads_router

# Create the main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(reports_router)
api_router.include_router(documents_router)
api_router.include_router(formats_router)
api_router.include_router(agents_router)
api_router.include_router(uploads_router)
api_router.include_router(tasks_router)
api_router.include_router(generate_router, prefix="/generate")  # Add generate router with prefix

# Export the API router
__all__ = ["api_router"]
