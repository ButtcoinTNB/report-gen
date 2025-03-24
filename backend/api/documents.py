from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
from ..models.document import DocumentMetadata, DocumentMetadataUpdate
from ..services.document_service import DocumentService
from ..utils.validation import validate_url
from ..dependencies import get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/metadata", response_model=APIResponse[DocumentMetadata])
async def get_document_metadata(
    url: str,
    document_service: DocumentService = Depends(get_document_service)
) -> APIResponse[DocumentMetadata]:
    """
    Retrieve metadata for a document by its URL.
    
    Args:
        url: The URL of the document to analyze
        document_service: Injected document service
        
    Returns:
        Document metadata including page count and other properties
        
    Raises:
        HTTPException: If the document cannot be found or analyzed
    """
    try:
        if not validate_url(url):
            raise ValueError("Invalid document URL")
            
        metadata = await document_service.get_metadata(url)
        return APIResponse(
            data=metadata,
            message="Document metadata retrieved successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document metadata: {str(e)}"
        )

@router.get("/{document_id}/metadata", response_model=DocumentMetadata)
async def get_document_metadata(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentMetadata:
    """
    Retrieve metadata for a specific document.
    """
    try:
        metadata = await document_service.get_metadata(document_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{document_id}/metadata", response_model=DocumentMetadata)
async def update_document_metadata(
    document_id: str,
    metadata: DocumentMetadataUpdate,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentMetadata:
    """
    Update metadata for a specific document.
    """
    try:
        updated_metadata = await document_service.update_metadata(document_id, metadata)
        if not updated_metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        return updated_metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 