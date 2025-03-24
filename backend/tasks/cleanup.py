import asyncio
from datetime import datetime

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings
    from utils.supabase_helper import create_supabase_client
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import get_settings
    from backend.utils.supabase_helper import create_supabase_client


async def cleanup_expired_share_links():
    """
    Background task to clean up expired share links.
    This task runs periodically to remove expired share links from the database.
    """
    get_settings()
    client = create_supabase_client()

    while True:
        try:
            now = datetime.utcnow()

            # Delete expired share links
            response = (
                await client.table("share_links")
                .delete()
                .lt("expires_at", now.isoformat())
                .execute()
            )

            if response.error:
                print(
                    f"Error cleaning up expired share links: {response.error.message}"
                )
            else:
                deleted_count = len(response.data) if response.data else 0
                if deleted_count > 0:
                    print(f"Cleaned up {deleted_count} expired share links")

            # Sleep for 1 hour before next cleanup
            await asyncio.sleep(3600)

        except Exception as e:
            print(f"Error in cleanup task: {str(e)}")
            # Sleep for 5 minutes before retrying on error
            await asyncio.sleep(300)


async def start_cleanup_tasks():
    """Start all cleanup tasks."""
    asyncio.create_task(cleanup_expired_share_links())
