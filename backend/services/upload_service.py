"""
Service for handling file uploads to Supabase storage.
"""

import os
import uuid
from datetime import datetime
from typing import Any, BinaryIO, Dict, Optional

from utils.supabase_helper import async_supabase_client_context


class UploadService:
    def __init__(self):
        # Don't initialize supabase directly in __init__, use context manager in methods
        pass

    async def upload_template(
        self,
        file: BinaryIO,
        filename: str,
        user_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a template file to Supabase storage and create a database record.
        """
        # Generate a unique filename
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        storage_path = f"templates/{unique_filename}"

        async with async_supabase_client_context() as supabase:
            # Upload file to storage
            await supabase.storage.from_("templates").upload(storage_path, file)

            # Create template record in database matching exact schema
            response = await supabase.table("templates").insert({
                "name": filename,
                "description": description or "",
                "storage_path": storage_path,
                "created_by": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()

            if not response.data:
                raise Exception("Failed to create template record")

            return response.data[0]

    async def upload_reference_report(
        self,
        file: BinaryIO,
        filename: str,
        template_id: str,
        user_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a reference report file to Supabase storage and create a database record.
        """
        # Generate a unique filename
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        storage_path = f"reference_reports/{unique_filename}"

        async with async_supabase_client_context() as supabase:
            # Upload file to storage
            await supabase.storage.from_("reports").upload(storage_path, file)

            # Create reference report record in database matching exact schema
            response = await supabase.table("reference_reports").insert({
                "name": filename,
                "description": description or "",
                "template_id": template_id,
                "storage_path": storage_path,
                "created_by": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()

            if not response.data:
                raise Exception("Failed to create reference report record")

            return response.data[0]

    async def upload_report(
        self,
        file: BinaryIO,
        filename: str,
        reference_report_id: str,
        user_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a generated report file to Supabase storage and create a database record.
        """
        # Generate a unique filename
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        storage_path = f"reports/{timestamp}_{unique_filename}"

        async with async_supabase_client_context() as supabase:
            # Upload file to storage
            await supabase.storage.from_("reports").upload(storage_path, file)

            # Create report record in database matching exact schema
            response = await supabase.table("reports").insert({
                "name": filename,
                "description": description or "",
                "reference_report_id": reference_report_id,
                "storage_path": storage_path,
                "created_by": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()

            if not response.data:
                raise Exception("Failed to create report record")

            return response.data[0]

    async def get_file_url(
        self, bucket: str, file_path: str, expires_in: int = 3600
    ) -> str:
        """
        Get a signed URL for accessing a file.
        """
        async with async_supabase_client_context() as supabase:
            return await supabase.storage.from_(bucket).create_signed_url(
                file_path, expires_in=expires_in
            )


# Create a singleton instance
upload_service = UploadService()
