"""
Service for managing share links.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, cast

from supabase._async.client import AsyncClient as SupabaseClient

from ..config import get_settings
from ..models import ShareLink, ShareLinkResponse
from ..types.supabase import APIResponse, SingleAPIResponse
from ..utils.supabase_helper import create_supabase_client


class ShareService:
    def __init__(self):
        self.settings = get_settings()
        self.supabase: Optional[SupabaseClient] = None

    async def initialize(self):
        """Initialize the Supabase client"""
        if self.supabase is None:
            self.supabase = await create_supabase_client()

    async def create_share_link(
        self, document_id: str, expires_in: int, max_downloads: int
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
            await self.initialize()
            assert self.supabase is not None

            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            share_link = ShareLink(
                token=token,
                document_id=document_id,
                expires_at=expires_at,
                max_downloads=max_downloads,
                remaining_downloads=max_downloads,
                created_at=datetime.utcnow(),
            )

            response: APIResponse[Dict[str, Any]] = cast(
                APIResponse[Dict[str, Any]],
                await self.supabase.table("share_links")
                .insert(share_link.dict(exclude_none=True))
                .execute()
            )

            if response.error:
                raise Exception(response.error.message)

            base_url = self.settings.BASE_URL.rstrip("/")
            share_url = f"{base_url}/share/{token}"

            return ShareLinkResponse(
                url=share_url,
                token=token,
                expires_at=expires_at,
                remaining_downloads=max_downloads,
                document_id=document_id,
            )

        except Exception as e:
            raise Exception(f"Failed to create share link: {str(e)}")

    async def get_share_link(self, token: str) -> Optional[ShareLink]:
        """
        Get a share link by its token.

        Args:
            token: The share link token

        Returns:
            ShareLink object if found, None otherwise
        """
        try:
            await self.initialize()
            assert self.supabase is not None

            response: SingleAPIResponse[Dict[str, Any]] = cast(
                SingleAPIResponse[Dict[str, Any]],
                await self.supabase.table("share_links")
                .select("*")
                .eq("token", token)
                .single()
                .execute()
            )

            if response.error:
                raise Exception(response.error.message)

            if not response.data:
                return None

            return ShareLink(**response.data)

        except Exception as e:
            raise Exception(f"Failed to get share link: {str(e)}")

    async def update_remaining_downloads(self, token: str, remaining_downloads: int) -> None:
        """
        Update the remaining downloads for a share link.

        Args:
            token: The share link token
            remaining_downloads: New remaining downloads value
        """
        try:
            await self.initialize()
            assert self.supabase is not None

            response: APIResponse[Dict[str, Any]] = cast(
                APIResponse[Dict[str, Any]],
                await self.supabase.table("share_links")
                .update({"remaining_downloads": remaining_downloads})
                .eq("token", token)
                .execute()
            )

            if response.error:
                raise Exception(response.error.message)

        except Exception as e:
            raise Exception(f"Failed to update remaining downloads: {str(e)}")

    async def get_share_links_by_document(self, document_id: str) -> List[ShareLink]:
        """
        Get all share links for a document.

        Args:
            document_id: ID of the document

        Returns:
            List of ShareLink objects
        """
        try:
            await self.initialize()
            assert self.supabase is not None

            response: APIResponse[Dict[str, Any]] = cast(
                APIResponse[Dict[str, Any]],
                await self.supabase.table("share_links")
                .select("*")
                .eq("document_id", document_id)
                .execute()
            )

            if response.error:
                raise Exception(response.error.message)

            return [ShareLink(**item) for item in response.data]

        except Exception as e:
            raise Exception(f"Failed to get share links: {str(e)}")

    async def delete_share_link(self, token: str) -> None:
        """
        Delete a share link.

        Args:
            token: The share link token
        """
        try:
            await self.initialize()
            assert self.supabase is not None

            response: APIResponse[Dict[str, Any]] = cast(
                APIResponse[Dict[str, Any]],
                await self.supabase.table("share_links")
                .delete()
                .eq("token", token)
                .execute()
            )

            if response.error:
                raise Exception(response.error.message)

        except Exception as e:
            raise Exception(f"Failed to delete share link: {str(e)}")

    async def cleanup_expired_links(self) -> None:
        """Delete all expired share links."""
        try:
            await self.initialize()
            assert self.supabase is not None

            response: APIResponse[Dict[str, Any]] = cast(
                APIResponse[Dict[str, Any]],
                await self.supabase.table("share_links")
                .delete()
                .lt("expires_at", datetime.utcnow())
                .execute()
            )

            if response.error:
                raise Exception(response.error.message)

        except Exception as e:
            raise Exception(f"Failed to cleanup expired links: {str(e)}")

    def __del__(self):
        """Cleanup when the service is destroyed."""
        if hasattr(self, "supabase"):
            # Close any open connections
            pass
