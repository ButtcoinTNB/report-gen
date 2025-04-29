from contextlib import asynccontextmanager
from typing import AsyncGenerator, TypeVar, Dict, Any
from supabase._async.client import AsyncClient
import logging

from utils.supabase_helper import async_supabase_client_context

logger = logging.getLogger(__name__)
T = TypeVar('T')

@asynccontextmanager
async def supabase_transaction() -> AsyncGenerator[AsyncClient, None]:
    """
    Async context manager that handles Supabase transactions.
    
    Yields:
        Supabase client with transaction context
        
    Example:
        async with supabase_transaction() as supabase:
            await supabase.from_("files").insert(file_data).execute()
            await supabase.from_("reports").update(report_data).eq("id", report_id).execute()
    """
    async with async_supabase_client_context() as supabase:
        try:
            # Start transaction
            await supabase.rpc('begin_transaction', {}).execute()
            
            yield supabase
            
            # Commit transaction
            await supabase.rpc('commit_transaction', {}).execute()
        except Exception as e:
            # Rollback on error
            try:
                await supabase.rpc('rollback_transaction', {}).execute()
            except Exception as rollback_error:
                logger.error(f"Error rolling back transaction: {str(rollback_error)}")
            raise e 