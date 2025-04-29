import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from postgrest import AsyncPostgrestClient

from models.file import FileRecord, FileUpdate
from services.text_extractor import extract_text_from_file
from utils.supabase_helper import async_supabase_client_context

logger = logging.getLogger(__name__)

class FileProcessor:
    """Service for processing uploaded files in the background."""
    
    def __init__(self, file_id: UUID):
        """
        Initialize the file processor.
        
        Args:
            file_id: UUID of the file to process
        """
        self.file_id = file_id
    
    async def process(self) -> None:
        """Process the file and update its record in the database."""
        try:
            async with async_supabase_client_context() as supabase:
                supabase_client = AsyncPostgrestClient(supabase)
                
                # Get file record
                response = await supabase_client.table("files").select("*").eq("file_id", str(self.file_id)).execute()
                if not response.data:
                    raise ValueError(f"File record not found: {self.file_id}")
                
                file_record = FileRecord.model_validate(response.data[0])
                
                # Extract text content
                content = await extract_text_from_file(file_record.file_path)
                
                # Update file record
                update = FileUpdate(
                    content=content,
                    status="processed",
                    metadata={
                        **file_record.metadata,
                        "processed_at": datetime.now().isoformat()
                    }
                )
                
                await supabase_client.table("files").update(update.model_dump(exclude_unset=True)).eq("file_id", str(self.file_id)).execute()
                
                logger.info(f"Successfully processed file: {file_record.filename}")
                
        except Exception as e:
            logger.error(f"Error processing file {self.file_id}: {str(e)}")
            # Update file status to error
            try:
                async with async_supabase_client_context() as supabase:
                    supabase_client = AsyncPostgrestClient(supabase)
                    update = FileUpdate(
                        status="error",
                        metadata={
                            "error": str(e),
                            "error_time": datetime.now().isoformat()
                        }
                    )
                    await supabase_client.table("files").update(update.model_dump(exclude_unset=True)).eq("file_id", str(self.file_id)).execute()
            except Exception as update_error:
                logger.error(f"Failed to update error status for file {self.file_id}: {str(update_error)}")
            raise 