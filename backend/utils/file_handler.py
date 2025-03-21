"""
File handler module that forwards imports from file_utils.py

This file exists to maintain backward compatibility with code that imports
from utils.file_handler but should use utils.file_utils instead.
"""

# Import and re-export functions from file_utils for backward compatibility
from utils.file_utils import safe_path_join, get_safe_file_paths, is_safe_path
from utils.storage import save_uploaded_file, delete_uploaded_file
from utils.file_processor import get_file_info

# Add a warning log
import logging
logger = logging.getLogger(__name__)
logger.warning("Importing from utils.file_handler is deprecated. Please update to use appropriate modules.") 