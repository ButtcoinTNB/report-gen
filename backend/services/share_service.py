"""
Service for managing share links.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, cast

from supabase._async.client import AsyncClient

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings
    from models import ShareLink, ShareLinkResponse
    from app_types.supabase import APIResponse, SingleAPIResponse
    from utils.supabase_helper import async_supabase_client_context
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import get_settings
    from backend.models import ShareLink, ShareLinkResponse
    from backend.app_types.supabase import APIResponse, SingleAPIResponse
    from backend.utils.supabase_helper import async_supabase_client_context


class ShareService:
    def __init__(self):
        self.settings = get_settings()

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
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            share_link = ShareLink(
                token=token,
                document_id=document_id,
                expires_at=expires_at,
                max_downloads=max_downloads,
                remaining_downloads=max_downloads,
                created_at=datetime.now(timezone.utc),
            )

            async with async_supabase_client_context() as supabase:
                client: AsyncClient = cast(AsyncClient, supabase)
                response: APIResponse[Dict[str, Any]] = cast(
                    APIResponse[Dict[str, Any]],
                    await client.table("share_links")
                    .insert(share_link.model_dump(exclude_none=True))
                    .execute(),
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
            async with async_supabase_client_context() as supabase:
                response: SingleAPIResponse[Dict[str, Any]] = cast(
                    SingleAPIResponse[Dict[str, Any]],
                    await supabase.table("share_links")
                    .select("*")
                    .eq("token", token)
                    .single()
                    .execute(),
                )

                if response.error:
                    raise Exception(response.error.message)

                if not response.data:
                    return None

                return ShareLink(**response.data)

        except Exception as e:
            raise Exception(f"Failed to get share link: {str(e)}")

    async def update_remaining_downloads(
        self, token: str, remaining_downloads: int
    ) -> None:
        """
        Update the remaining downloads for a share link.

        Args:
            token: The share link token
            remaining_downloads: New remaining downloads value
        """
        try:
            async with async_supabase_client_context() as supabase:
                response: APIResponse[Dict[str, Any]] = cast(
                    APIResponse[Dict[str, Any]],
                    await supabase.table("share_links")
                    .update({"remaining_downloads": remaining_downloads})
                    .eq("token", token)
                    .execute(),
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
            async with async_supabase_client_context() as supabase:
                response: APIResponse[Dict[str, Any]] = cast(
                    APIResponse[Dict[str, Any]],
                    await supabase.table("share_links")
                    .select("*")
                    .eq("document_id", document_id)
                    .execute(),
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
            async with async_supabase_client_context() as supabase:
                response: APIResponse[Dict[str, Any]] = cast(
                    APIResponse[Dict[str, Any]],
                    await supabase.table("share_links")
                    .delete()
                    .eq("token", token)
                    .execute(),
                )

                if response.error:
                    raise Exception(response.error.message)

        except Exception as e:
            raise Exception(f"Failed to delete share link: {str(e)}")

    async def cleanup_expired_links(self) -> None:
        """Delete all expired share links."""
        try:
            async with async_supabase_client_context() as supabase:
                response: APIResponse[Dict[str, Any]] = cast(
                    APIResponse[Dict[str, Any]],
                    await supabase.table("share_links")
                    .delete()
                    .lt("expires_at", datetime.utcnow().isoformat())
                    .execute(),
                )

                if response.error:
                    raise Exception(response.error.message)

        except Exception as e:
            raise Exception(f"Failed to cleanup expired links: {str(e)}")

    async def share_report(self, report_id: str, user_id: str) -> Dict[str, Any]:
        """
        Share a report with another user.
        """
        try:
            async with async_supabase_client_context() as supabase:
                # Check if report exists
                report_response = await supabase.table("reports") \
                    .select("*") \
                    .eq("report_id", report_id) \
                    .execute()

                if not report_response.data:
                    raise ValueError(f"Report not found: {report_id}")

                # Create share record
                share_response = await supabase.table("report_shares").insert({
                    "report_id": report_id,
                    "shared_with": user_id,
                    "created_at": datetime.now().isoformat()
                }).execute()

                return share_response.data[0]

        except Exception as e:
            raise Exception(f"Error sharing report: {str(e)}")

    async def get_shared_reports(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all reports shared with a user.
        """
        try:
            async with async_supabase_client_context() as supabase:
                response = await supabase.table("report_shares") \
                    .select("*, reports(*)") \
                    .eq("shared_with", user_id) \
                    .execute()

                return response.data if response.data else []

        except Exception as e:
            raise Exception(f"Error getting shared reports: {str(e)}")

    async def remove_share(self, report_id: str, user_id: str) -> bool:
        """
        Remove a report share.
        """
        try:
            async with async_supabase_client_context() as supabase:
                response = await supabase.table("report_shares") \
                    .delete() \
                    .eq("report_id", report_id) \
                    .eq("shared_with", user_id) \
                    .execute()

                return bool(response.data)

        except Exception as e:
            raise Exception(f"Error removing share: {str(e)}")

    async def get_share_info(self, report_id: str) -> List[Dict[str, Any]]:
        """
        Get sharing information for a report.
        """
        try:
            async with async_supabase_client_context() as supabase:
                response = await supabase.table("report_shares") \
                    .select("*, users(*)") \
                    .eq("report_id", report_id) \
                    .execute()

                return response.data if response.data else []

        except Exception as e:
            raise Exception(f"Error getting share info: {str(e)}")

    async def check_share_exists(self, report_id: str, user_id: str) -> bool:
        """
        Check if a report is shared with a user.
        """
        try:
            async with async_supabase_client_context() as supabase:
                response = await supabase.table("report_shares") \
                    .select("*") \
                    .eq("report_id", report_id) \
                    .eq("shared_with", user_id) \
                    .execute()

                return bool(response.data)

        except Exception as e:
            raise Exception(f"Error checking share: {str(e)}")

    async def get_report_permissions(self, report_id: str, user_id: str) -> Dict[str, bool]:
        """
        Get permissions for a user on a report.
        """
        try:
            async with async_supabase_client_context() as supabase:
                # Check if user owns the report
                owner_response = await supabase.table("reports") \
                    .select("*") \
                    .eq("report_id", report_id) \
                    .eq("created_by", user_id) \
                    .execute()

                is_owner = bool(owner_response.data)

                # Check if report is shared with user
                share_response = await supabase.table("report_shares") \
                    .select("*") \
                    .eq("report_id", report_id) \
                    .eq("shared_with", user_id) \
                    .execute()

                is_shared = bool(share_response.data)

                return {
                    "can_view": is_owner or is_shared,
                    "can_edit": is_owner,
                    "can_delete": is_owner,
                    "can_share": is_owner
                }

        except Exception as e:
            raise Exception(f"Error getting permissions: {str(e)}")
