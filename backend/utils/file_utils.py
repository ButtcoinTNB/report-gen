"""
File utility functions for secure file operations.
"""

import re
from pathlib import Path
from typing import List, Union, Generator, Optional
import os
import shutil
import uuid
from contextlib import contextmanager
import logging

from utils.error_handler import logger


# Custom secure_filename implementation without werkzeug dependency
def secure_filename(filename: str) -> str:
    """
    Return a secure version of a filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Secure filename string
    """
    filename = str(filename).strip().replace(" ", "_")
    filename = re.sub(r"(?u)[^-\w.]", "", filename)
    return filename


def safe_path_join(base: str, filename: str) -> str:
    """
    Safely join a base path and filename using pathlib.Path.
    
    Args:
        base: Base directory path
        filename: Name of the file to join
        
    Returns:
        Safe joined path as string
    """
    safe_name = secure_filename(filename)
    return str(Path(base) / safe_name)


def get_file_type(filename: str) -> str:
    """
    Get the file type from filename extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        File type string (e.g. 'pdf', 'docx')
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext.lstrip(".")


def get_mime_type(filename: str) -> str:
    """
    Get the MIME type for a file based on its extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        MIME type string
    """
    ext = get_file_type(filename)
    mime_types = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "rtf": "application/rtf",
        "odt": "application/vnd.oasis.opendocument.text"
    }
    return mime_types.get(ext, "application/octet-stream")


def get_safe_file_paths(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
    """
    Safely get file paths in a directory matching a pattern.

    Args:
        directory: The base directory to search in
        pattern: Glob pattern for matching files

    Returns:
        List of safe, absolute paths to files matching the pattern
    """
    base_path = Path(directory).resolve()
    if not base_path.exists() or not base_path.is_dir():
        logger.warning(f"Directory does not exist or is not a directory: {base_path}")
        return []

    # Use Path.glob which is safer than os.listdir with manual joining
    paths = []
    for path in base_path.glob(pattern):
        try:
            # Double-check that the path is safe
            safe_path = safe_path_join(base_path, path.name)
            paths.append(safe_path)
        except ValueError:
            logger.warning(f"Skipping unsafe path: {path}")

    return paths


def is_safe_path(base_dir: Union[str, Path], path: Union[str, Path]) -> bool:
    """
    Check if a path is safe (within the base directory).

    Args:
        base_dir: The base directory that should contain the path
        path: The path to check

    Returns:
        True if the path is safe, False otherwise
    """
    try:
        safe_path_join(Path(base_dir), Path(path).name)
        return True
    except ValueError:
        return False


@contextmanager
def temporary_directory(base_dir: str) -> Generator[str, None, None]:
    """
    Context manager that creates a temporary directory and ensures its cleanup.
    
    Args:
        base_dir: Base directory where the temporary directory will be created
        
    Yields:
        Path to the created temporary directory
        
    Ensures:
        Directory is cleaned up after use, even if an exception occurs
    """
    tmp_dir = os.path.join(base_dir, f"tmp_{str(uuid.uuid4())}")
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        yield tmp_dir
    finally:
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary directory {tmp_dir}: {str(e)}")
