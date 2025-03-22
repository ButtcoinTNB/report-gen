"""
Utility module for Supabase operations.
Provides a centralized way to interact with Supabase storage and database.
"""

import os
from typing import Optional, Dict, Any, BinaryIO
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseClient:
    _instance = None
    _client: Optional[Client] = None
    
    @classmethod
    def get_instance(cls) -> 'SupabaseClient':
        """Get singleton instance of SupabaseClient."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        if not self._client:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            
            self._client = create_client(supabase_url, supabase_key)
    
    def get_client(self) -> Client:
        """Get the Supabase client instance."""
        return self._client
    
    # Storage Operations
    async def upload_file(self, bucket: str, file_path: str, file: BinaryIO) -> str:
        """
        Upload a file to Supabase storage.
        Returns the file path in the bucket.
        """
        try:
            response = self._client.storage.from_(bucket).upload(file_path, file)
            return response
        except Exception as e:
            raise Exception(f"Error uploading file to Supabase: {str(e)}")
    
    async def get_file_url(self, bucket: str, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a signed URL for a file in Supabase storage.
        expires_in: URL expiration time in seconds (default: 1 hour)
        """
        try:
            signed_url = self._client.storage.from_(bucket).create_signed_url(file_path, expires_in)
            return signed_url
        except Exception as e:
            raise Exception(f"Error getting signed URL: {str(e)}")
    
    async def download_file(self, bucket: str, file_path: str) -> bytes:
        """Download a file from Supabase storage."""
        try:
            return self._client.storage.from_(bucket).download(file_path)
        except Exception as e:
            raise Exception(f"Error downloading file: {str(e)}")
    
    # Database Operations
    async def create_template(
        self, 
        name: str, 
        description: str, 
        storage_path: str, 
        created_by: str
    ) -> Dict[str, Any]:
        """Create a new template record."""
        try:
            data = {
                "name": name,
                "description": description,
                "storage_path": storage_path,
                "created_by": created_by
            }
            response = self._client.table("templates").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise Exception(f"Error creating template: {str(e)}")
    
    async def create_reference_report(
        self, 
        name: str,
        description: str,
        template_id: str, 
        storage_path: str, 
        created_by: str
    ) -> Dict[str, Any]:
        """Create a new reference report record."""
        try:
            data = {
                "name": name,
                "description": description,
                "template_id": template_id,
                "storage_path": storage_path,
                "created_by": created_by
            }
            response = self._client.table("reference_reports").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise Exception(f"Error creating reference report: {str(e)}")
    
    async def create_report(
        self,
        name: str,
        description: str,
        reference_report_id: str,
        storage_path: str,
        created_by: str
    ) -> Dict[str, Any]:
        """Create a new report record."""
        try:
            data = {
                "name": name,
                "description": description,
                "reference_report_id": reference_report_id,
                "storage_path": storage_path,
                "created_by": created_by
            }
            response = self._client.table("reports").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            raise Exception(f"Error creating report: {str(e)}")
    
    async def get_user_reports(self, user_id: str) -> list:
        """Get all reports for a specific user."""
        try:
            response = self._client.table("reports").select("*").eq("created_by", user_id).execute()
            return response.data
        except Exception as e:
            raise Exception(f"Error fetching user reports: {str(e)}")
    
    async def get_templates(self) -> list:
        """Get all available templates."""
        try:
            response = self._client.table("templates").select("*").execute()
            return response.data
        except Exception as e:
            raise Exception(f"Error fetching templates: {str(e)}")

# Create a singleton instance
supabase = SupabaseClient.get_instance() 