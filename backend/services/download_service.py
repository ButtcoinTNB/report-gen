"""
Service for handling file downloads and previews from Supabase storage.
"""

from typing import Optional, Dict, Any, BinaryIO
from utils.supabase_client import supabase

class DownloadService:
    def __init__(self):
        self.supabase = supabase
    
    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """
        Get template information and generate a download URL.
        """
        try:
            # Get template record
            response = self.supabase.get_client().table("templates") \
                .select("*") \
                .eq("id", template_id) \
                .single() \
                .execute()
            
            template = response.data
            if not template:
                raise ValueError(f"Template not found: {template_id}")
            
            # Generate download URL
            download_url = await self.supabase.get_file_url(
                "templates",
                template["storage_path"],
                expires_in=3600  # URL expires in 1 hour
            )
            
            template["download_url"] = download_url
            return template
            
        except Exception as e:
            raise Exception(f"Error getting template: {str(e)}")
    
    async def get_reference_report(self, report_id: str) -> Dict[str, Any]:
        """
        Get reference report information and generate a download URL.
        """
        try:
            # Get reference report record
            response = self.supabase.get_client().table("reference_reports") \
                .select("*") \
                .eq("id", report_id) \
                .single() \
                .execute()
            
            report = response.data
            if not report:
                raise ValueError(f"Reference report not found: {report_id}")
            
            # Generate download URL
            download_url = await self.supabase.get_file_url(
                "reports",
                report["storage_path"],
                expires_in=3600  # URL expires in 1 hour
            )
            
            report["download_url"] = download_url
            return report
            
        except Exception as e:
            raise Exception(f"Error getting reference report: {str(e)}")
    
    async def get_report(self, report_id: str) -> Dict[str, Any]:
        """
        Get report information and generate a download URL.
        """
        try:
            # Get report record
            response = self.supabase.get_client().table("reports") \
                .select("*") \
                .eq("id", report_id) \
                .single() \
                .execute()
            
            report = response.data
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            # Generate download URL
            download_url = await self.supabase.get_file_url(
                "reports",
                report["storage_path"],
                expires_in=3600  # URL expires in 1 hour
            )
            
            report["download_url"] = download_url
            return report
            
        except Exception as e:
            raise Exception(f"Error getting report: {str(e)}")
    
    async def download_file(self, bucket: str, file_path: str) -> bytes:
        """
        Download a file directly from Supabase storage.
        """
        return await self.supabase.download_file(bucket, file_path)

# Create a singleton instance
download_service = DownloadService() 