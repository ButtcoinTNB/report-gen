from datetime import datetime
from io import BytesIO
from typing import Optional

import aiohttp
import PyPDF2

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import get_settings
    from database import get_db
    from models import DocumentMetadata
    from models.document import DocumentMetadataUpdate
    from storage import get_storage
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import get_settings
    from backend.database import get_db
    from backend.models import DocumentMetadata
    from backend.models.document import DocumentMetadataUpdate
    from backend.storage import get_storage


class DocumentService:
    def __init__(self, db=None, storage=None):
        self.db = db or get_db()
        self.storage = storage or get_storage()
        self.settings = get_settings()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_metadata(self, document_id: str) -> Optional[DocumentMetadata]:
        """
        Retrieve metadata for a specific document.
        """
        try:
            result = (
                await self.db.table("documents")
                .select("*")
                .eq("id", document_id)
                .single()
                .execute()
            )
            if result.data:
                return DocumentMetadata(**result.data)
            return None
        except Exception as e:
            raise Exception(f"Failed to retrieve document metadata: {str(e)}")

    async def update_metadata(
        self, document_id: str, metadata: DocumentMetadataUpdate
    ) -> Optional[DocumentMetadata]:
        """
        Update metadata for a specific document.
        """
        try:
            # Convert Pydantic model to dict and remove None values
            update_data = metadata.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow().isoformat()

            result = (
                await self.db.table("documents")
                .update(update_data)
                .eq("id", document_id)
                .execute()
            )
            if result.data:
                return DocumentMetadata(**result.data[0])
            return None
        except Exception as e:
            raise Exception(f"Failed to update document metadata: {str(e)}")

    async def increment_download_count(
        self, document_id: str
    ) -> Optional[DocumentMetadata]:
        """
        Increment the download count for a document and update last_downloaded_at.
        """
        try:
            update_data = {
                "download_count": self.db.raw("download_count + 1"),
                "last_downloaded_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = (
                await self.db.table("documents")
                .update(update_data)
                .eq("id", document_id)
                .execute()
            )
            if result.data:
                return DocumentMetadata(**result.data[0])
            return None
        except Exception as e:
            raise Exception(f"Failed to update document download count: {str(e)}")

    async def get_download_url(self, document_id: str) -> str:
        """
        Get a temporary download URL for a document.
        """
        try:
            metadata = await self.get_metadata(document_id)
            if not metadata:
                raise Exception("Document not found")

            # Generate a signed URL that expires in 1 hour
            url = await self.storage.create_signed_url(
                bucket="reports", path=f"{document_id}/report.docx", expires_in=3600
            )
            return url
        except Exception as e:
            raise Exception(f"Failed to generate download URL: {str(e)}")

    async def cleanup_temporary_files(self, document_id: str) -> None:
        """
        Clean up any temporary files associated with a document.
        """
        try:
            # Delete temporary files from storage
            await self.storage.delete_folder(bucket="temp", path=f"{document_id}/")
        except Exception as e:
            raise Exception(f"Failed to cleanup temporary files: {str(e)}")

    async def delete_document(self, document_id: str) -> None:
        """
        Delete a document and all associated files.
        """
        try:
            # Delete from storage first
            await self.storage.delete_folder(bucket="reports", path=f"{document_id}/")

            # Then delete from database
            await self.db.table("documents").delete().eq("id", document_id).execute()
        except Exception as e:
            raise Exception(f"Failed to delete document: {str(e)}")

    async def get_metadata_by_url(self, url: str) -> DocumentMetadata:
        """
        Retrieve metadata for a document by analyzing its content.

        Args:
            url: The URL of the document to analyze

        Returns:
            DocumentMetadata object containing document properties

        Raises:
            ValueError: If the document cannot be accessed or is invalid
            Exception: For other processing errors
        """
        try:
            session = await self._get_session()

            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to fetch document: {response.status}")

                content = await response.read()
                content_type = response.headers.get("content-type", "")

                if "pdf" in content_type.lower():
                    return await self._get_pdf_metadata(content)
                elif "docx" in content_type.lower():
                    return await self._get_docx_metadata(content)
                else:
                    raise ValueError(f"Unsupported document type: {content_type}")

        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to fetch document: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing document: {str(e)}")

    async def _get_pdf_metadata(self, content: bytes) -> DocumentMetadata:
        """Extract metadata from PDF content."""
        try:
            pdf = PyPDF2.PdfReader(BytesIO(content))

            return DocumentMetadata(
                page_count=len(pdf.pages),
                file_size=len(content),
                content_type="application/pdf",
                is_encrypted=pdf.is_encrypted,
                title=pdf.metadata.get("/Title", None) if pdf.metadata else None,
            )
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")

    async def _get_docx_metadata(self, content: bytes) -> DocumentMetadata:
        """Extract metadata from DOCX content."""
        try:
            # For now, return basic metadata
            # TODO: Implement proper DOCX metadata extraction
            return DocumentMetadata(
                page_count=1,  # Placeholder
                file_size=len(content),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as e:
            raise Exception(f"Error processing DOCX: {str(e)}")

    def __del__(self):
        """Ensure the session is closed on service cleanup."""
        if self._session and not self._session.closed:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._session.close())
            else:
                loop.run_until_complete(self._session.close())
