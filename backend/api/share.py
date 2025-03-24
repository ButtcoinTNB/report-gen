from fastapi import APIRouter, HTTPException, Depends
from ..models.share import ShareLinkCreate, ShareLinkResponse
from ..services.share_service import ShareService
from ..config import get_settings

router = APIRouter()

@router.post("/create", response_model=ShareLinkResponse)
async def create_share_link(
    data: ShareLinkCreate,
    settings = Depends(get_settings),
    share_service: ShareService = Depends(lambda: ShareService())
) -> ShareLinkResponse:
    """
    Create a new share link for a document.
    
    Args:
        data: Share link creation parameters
        settings: Application settings
        share_service: Share service instance
        
    Returns:
        ShareLinkResponse object containing the share link details
        
    Raises:
        HTTPException: If share link creation fails
    """
    try:
        return await share_service.create_share_link(
            document_id=data.document_id,
            expires_in=data.expires_in,
            max_downloads=data.max_downloads
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create share link: {str(e)}"
        )

@router.get("/{token}", response_model=ShareLinkResponse)
async def get_share_link(
    token: str,
    share_service: ShareService = Depends(lambda: ShareService())
) -> ShareLinkResponse:
    """
    Get information about a share link.
    
    Args:
        token: Share link token
        share_service: Share service instance
        
    Returns:
        ShareLinkResponse object containing the share link details
        
    Raises:
        HTTPException: If share link is not found or expired
    """
    try:
        share_link = await share_service.get_share_link(token)
        if not share_link:
            raise HTTPException(
                status_code=404,
                detail="Share link not found or expired"
            )
        return share_link
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get share link: {str(e)}"
        )

@router.delete("/{token}")
async def revoke_share_link(
    token: str,
    share_service: ShareService = Depends(lambda: ShareService())
) -> dict:
    """
    Revoke a share link.
    
    Args:
        token: Share link token
        share_service: Share service instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If share link revocation fails
    """
    try:
        await share_service.revoke_share_link(token)
        return {"message": "Share link revoked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke share link: {str(e)}"
        )

@router.post("/{token}/download")
async def track_download(
    token: str,
    share_service: ShareService = Depends(lambda: ShareService())
) -> dict:
    """
    Track a download for a share link.
    
    Args:
        token: Share link token
        share_service: Share service instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If download tracking fails
    """
    try:
        await share_service.track_download(token)
        return {"message": "Download tracked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track download: {str(e)}"
        ) 