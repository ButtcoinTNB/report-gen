"""
File handler module that forwards imports from file_utils.py

This file exists to maintain backward compatibility with code that imports
from utils.file_handler but should use utils.file_utils instead.
"""

# Import and re-export functions from file_utils for backward compatibility
from backend.utils.file_utils import safe_path_join, get_safe_file_paths, is_safe_path
from backend.utils.file_processor import FileProcessor

# Define the compatibility functions that redirect to FileProcessor
def save_uploaded_file(file, directory, filename=None):
    """Redirect to FileProcessor.save_upload"""
    return FileProcessor.save_upload(file, directory, filename)

def delete_uploaded_file(file_path):
    """Redirect to FileProcessor.delete_file"""
    return FileProcessor.delete_file(file_path)

def get_file_info(file_path):
    """Redirect to FileProcessor.get_file_info"""
    return FileProcessor.get_file_info(file_path)

# Add a warning log
import logging
logger = logging.getLogger(__name__)
logger.warning("Importing from utils.file_handler is deprecated. Please update to use appropriate modules.") 