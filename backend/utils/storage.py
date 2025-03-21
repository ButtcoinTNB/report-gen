"""
Storage utility functions for handling file paths and checking file existence.
"""
import os
from pathlib import Path
import re
from typing import Optional, Tuple
from pydantic import UUID4
from config import settings
from backend.utils.file_utils import safe_path_join

def validate_path(path: str, base_dir: str) -> Tuple[bool, str]:
    """
    Validate that a path is safe and doesn't allow directory traversal.
    
    Args:
        path: The path to validate
        base_dir: The base directory that the path should be confined to
        
    Returns:
        Tuple of (is_valid, normalized_path)
    """
    # Normalize the paths
    base_dir = os.path.normpath(os.path.abspath(base_dir))
    
    # Remove any "junk" from the path (like null bytes)
    cleaned_path = path.replace('\0', '')
    
    # Check that the UUID part of the path matches the expected UUID format
    # This is an additional security check, assuming paths contain UUIDs
    if "/" in cleaned_path or "\\" in cleaned_path:
        # If path contains directory separators, extract the UUID part
        path_parts = re.split(r'[/\\]', cleaned_path)
        for part in path_parts:
            # Check if this part looks like a UUID
            if len(part) == 36 and "-" in part:
                # Simple UUID pattern check (not comprehensive)
                uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
                if not re.match(uuid_pattern, part.lower()):
                    return False, ""
    
    try:
        # Use safe_path_join which will validate the path
        full_path = safe_path_join(base_dir, cleaned_path)
        return True, str(full_path)
    except ValueError:
        return False, ""


def get_report_path(report_id: UUID4) -> str:
    """
    Get the file path for a report based on its ID.
    
    Args:
        report_id: UUID of the report
        
    Returns:
        str: Path to the report file
    """
    # Convert the UUID to string if it's not already
    report_id_str = str(report_id)
    
    # Define the base directory for reports
    reports_dir = os.path.abspath("generated_reports")
    
    # Ensure the directory exists
    os.makedirs(reports_dir, exist_ok=True)
    
    try:
        # Use safe_path_join to get a secure path
        return str(safe_path_join(reports_dir, f"{report_id_str}.docx"))
    except ValueError as e:
        raise ValueError(f"Invalid report ID format: {report_id_str}") from e


def get_document_path(document_id: UUID4) -> str:
    """
    Get the file path for an uploaded document based on its ID.
    
    Args:
        document_id: UUID of the document
        
    Returns:
        str: Path to the document file
    """
    # Convert the UUID to string if it's not already
    document_id_str = str(document_id)
    
    # Get the uploads directory from settings
    uploads_dir = os.path.abspath(settings.UPLOAD_DIR)
    
    try:
        # Construct a path for the document directory using safe_path_join
        document_dir = safe_path_join(uploads_dir, document_id_str)
        
        # Create it if it doesn't exist
        os.makedirs(document_dir, exist_ok=True)
        
        # Return the directory path
        return str(document_dir)
    except ValueError as e:
        raise ValueError(f"Invalid document ID format: {document_id_str}") from e


def does_file_exist(file_path: str) -> bool:
    """
    Check if a file exists at the given path.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if the file exists, False otherwise
    """
    # Ensure the path is safe
    base_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    try:
        validated_path = safe_path_join(base_dir, file_name)
        return os.path.isfile(validated_path)
    except ValueError:
        return False


def get_safe_file_path(base_dir: str, file_path: str) -> Optional[str]:
    """
    Get a safe file path that prevents directory traversal.
    
    Args:
        base_dir: The base directory that the path should be confined to
        file_path: The relative path to the file
        
    Returns:
        Optional[str]: The safe absolute path or None if path is invalid
    """
    try:
        return str(safe_path_join(base_dir, file_path))
    except ValueError:
        return None 