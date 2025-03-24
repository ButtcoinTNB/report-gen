from fastapi import APIRouter, Depends, HTTPException

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings
    from models.share import ShareLinkCreate, ShareLinkResponse
    from services.share_service import ShareService
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import get_settings
    from backend.models.share import ShareLinkCreate, ShareLinkResponse
    from backend.services.share_service import ShareService

router = APIRouter()


@router.post("/create", response_model=ShareLinkResponse)
async def create_share_link(
    data: ShareLinkCreate,
    settings=Depends(get_settings),
    share_service: ShareService = Depends(lambda: ShareService()),
) -> ShareLinkResponse:
    """
    Create a new share link for a document.

    Args:
        data: Share link creation parameters
        settings: Application settings
        share_service: Share service instance

    Returns:
        The created share link information

    Raises:
        HTTPException: If the document doesn't exist or other errors occur
    """
    try:
        return await share_service.create_share_link(data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create share link: {str(e)}"
        )


@router.get("/{token}", response_model=ShareLinkResponse)
async def get_share_link(
    token: str, share_service: ShareService = Depends(lambda: ShareService())
) -> ShareLinkResponse:
    """
    Get information about a share link.

    Args:
        token: The share link token
        share_service: Share service instance

    Returns:
        The share link information

    Raises:
        HTTPException: If the share link doesn't exist or has expired
    """
    try:
        share_link = await share_service.get_share_link(token)
        if not share_link:
            raise HTTPException(
                status_code=404, detail="Share link not found or has expired"
            )
        return share_link
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve share link: {str(e)}"
        )


@router.delete("/{token}")
async def revoke_share_link(
    token: str, share_service: ShareService = Depends(lambda: ShareService())
) -> dict:
    """
    Revoke a share link.

    Args:
        token: The share link token
        share_service: Share service instance

    Returns:
        Success message

    Raises:
        HTTPException: If the share link doesn't exist or other errors occur
    """
    try:
        success = await share_service.revoke_share_link(token)
        if not success:
            raise HTTPException(status_code=404, detail="Share link not found")
        return {"message": "Share link successfully revoked"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to revoke share link: {str(e)}"
        )


@router.post("/{token}/download")
async def track_download(
    token: str, share_service: ShareService = Depends(lambda: ShareService())
) -> dict:
    """
    Track a document download via a share link.

    Args:
        token: The share link token
        share_service: Share service instance

    Returns:
        Download URL

    Raises:
        HTTPException: If the share link doesn't exist or has expired
    """
    try:
        download_url = await share_service.track_download(token)
        if not download_url:
            raise HTTPException(
                status_code=404, detail="Share link not found or has expired"
            )
        return {"download_url": download_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process download request: {str(e)}"
        )
