"""
Service for handling file uploads to Supabase storage.
"""

import os
import uuid
from datetime import datetime
from typing import Any, BinaryIO, Dict, Optional

from ..utils.supabase_client import supabase


class UploadService:
    def __init__(self):
        self.supabase = supabase

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

        # Upload file to storage
        await self.supabase.upload_file("templates", storage_path, file)

        # Create template record in database matching exact schema
        template = await self.supabase.create_template(
            name=filename,
            description=description or "",
            storage_path=storage_path,
            created_by=user_id,
        )

        return template

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

        # Upload file to storage
        await self.supabase.upload_file("reports", storage_path, file)

        # Create reference report record in database matching exact schema
        reference_report = await self.supabase.create_reference_report(
            name=filename,
            description=description or "",
            template_id=template_id,
            storage_path=storage_path,
            created_by=user_id,
        )

        return reference_report

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
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"reports/{timestamp}_{unique_filename}"

        # Upload file to storage
        await self.supabase.upload_file("reports", storage_path, file)

        # Create report record in database matching exact schema
        report = await self.supabase.create_report(
            name=filename,
            description=description or "",
            reference_report_id=reference_report_id,
            storage_path=storage_path,
            created_by=user_id,
        )

        return report

    async def get_file_url(
        self, bucket: str, file_path: str, expires_in: int = 3600
    ) -> str:
        """
        Get a signed URL for accessing a file.
        """
        return await self.supabase.get_file_url(bucket, file_path, expires_in)


# Create a singleton instance
upload_service = UploadService()
