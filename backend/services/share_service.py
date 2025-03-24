from typing import Optional
from datetime import datetime, timedelta
import secrets
from ..models import ShareLink, ShareLinkResponse
from ..config import get_settings
from ..utils.validation import validate_token
from ..utils.supabase_helper import create_supabase_client

class ShareService:
    def __init__(self):
        self.settings = get_settings()
        self.supabase = create_supabase_client()

    async def create_share_link(
        self,
        document_id: str,
        expires_in: int,
        max_downloads: int
    ) -> ShareLinkResponse:
        """
        Create a new share link for a document.
        
        Args:
            document_id: ID of the document to share
            expires_in: Expiration time in seconds
            max_downloads: Maximum number of downloads allowed
            
        Returns:
            ShareLinkResponse object containing the share link details
        """
        try:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            share_link = ShareLink(
                token=token,
                document_id=document_id,
                expires_at=expires_at,
                max_downloads=max_downloads,
                remaining_downloads=max_downloads,
                created_at=datetime.utcnow()
            )
            
            response = await self.supabase.table("share_links").insert(
                share_link.dict(exclude_none=True)
            ).execute()
            
            if response.error:
                raise Exception(response.error.message)
                
            base_url = self.settings.BASE_URL.rstrip('/')
            share_url = f"{base_url}/share/{token}"
            
            return ShareLinkResponse(
                url=share_url,
                token=token,
                expires_at=expires_at,
                remaining_downloads=max_downloads,
                document_id=document_id
            )
            
        except Exception as e:
            raise Exception(f"Failed to create share link: {str(e)}")

    async def get_share_link(self, token: str) -> Optional[ShareLinkResponse]:
        """
        Get information about a share link.
        
        Args:
            token: Share link token
            
        Returns:
            ShareLinkResponse object if found, None otherwise
        """
        try:
            response = await self.supabase.table("share_links").select("*").eq(
                "token", token
            ).single().execute()
            
            if response.error:
                raise Exception(response.error.message)
                
            if not response.data:
                return None
                
            share_link = ShareLink(**response.data)
            
            # Check if expired
            if share_link.expires_at < datetime.utcnow():
                await self.revoke_share_link(token)
                return None
                
            # Check if downloads exhausted
            if share_link.remaining_downloads <= 0:
                await self.revoke_share_link(token)
                return None
                
            base_url = self.settings.BASE_URL.rstrip('/')
            share_url = f"{base_url}/share/{token}"
            
            return ShareLinkResponse(
                url=share_url,
                token=token,
                expires_at=share_link.expires_at,
                remaining_downloads=share_link.remaining_downloads,
                document_id=share_link.document_id
            )
            
        except Exception as e:
            raise Exception(f"Failed to get share link: {str(e)}")

    async def revoke_share_link(self, token: str) -> None:
        """
        Revoke a share link.
        
        Args:
            token: Share link token
        """
        try:
            response = await self.supabase.table("share_links").delete().eq(
                "token", token
            ).execute()
            
            if response.error:
                raise Exception(response.error.message)
                
        except Exception as e:
            raise Exception(f"Failed to revoke share link: {str(e)}")

    async def track_download(self, token: str) -> None:
        """
        Track a download for a share link.
        
        Args:
            token: Share link token
        """
        try:
            # Get current share link
            response = await self.supabase.table("share_links").select("*").eq(
                "token", token
            ).single().execute()
            
            if response.error:
                raise Exception(response.error.message)
                
            if not response.data:
                raise Exception("Share link not found")
                
            share_link = ShareLink(**response.data)
            
            # Update remaining downloads
            new_remaining = max(0, share_link.remaining_downloads - 1)
            
            update_response = await self.supabase.table("share_links").update({
                "remaining_downloads": new_remaining,
                "last_downloaded_at": datetime.utcnow().isoformat()
            }).eq("token", token).execute()
            
            if update_response.error:
                raise Exception(update_response.error.message)
                
            # If no downloads remaining, revoke the link
            if new_remaining == 0:
                await self.revoke_share_link(token)
                
        except Exception as e:
            raise Exception(f"Failed to track download: {str(e)}")

    async def cleanup_expired_links(self) -> None:
        """Clean up expired share links."""
        try:
            now = datetime.utcnow()
            
            response = await self.supabase.table("share_links").delete().lt(
                "expires_at", now.isoformat()
            ).execute()
            
            if response.error:
                raise Exception(response.error.message)
                
        except Exception as e:
            raise Exception(f"Failed to cleanup expired links: {str(e)}")

    def __del__(self):
        """Cleanup when service is destroyed."""
        if hasattr(self, 'supabase'):
            # Close any open connections
            pass 