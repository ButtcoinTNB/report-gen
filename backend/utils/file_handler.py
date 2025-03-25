"""
File handling utilities for the Insurance Report Generator

This file exists to maintain backward compatibility with code that imports
from utils.file_handler but should use utils.file_utils instead.
"""

import logging
from utils.file_processor import FileProcessor

logger = logging.getLogger(__name__)


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
logger.warning(
    "Importing from utils.file_handler is deprecated. Please update to use appropriate modules."
)
