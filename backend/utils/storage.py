"""
Storage utility functions for handling file paths and checking file existence.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import UUID4

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
    # This should be adjusted based on your project's actual structure
    reports_dir = os.path.join(os.getcwd(), "generated_reports")
    
    # Ensure the directory exists
    os.makedirs(reports_dir, exist_ok=True)
    
    # Return the path with .docx extension
    return os.path.join(reports_dir, f"{report_id_str}.docx")

def does_file_exist(file_path: str) -> bool:
    """
    Check if a file exists at the given path.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if the file exists, False otherwise
    """
    return os.path.isfile(file_path) 