"""
File utility functions for secure file operations.
"""

from pathlib import Path
from typing import Union, List
import os
import re
from utils.error_handler import logger

# Custom secure_filename implementation without werkzeug dependency
def secure_filename(filename: str) -> str:
    """
    Pass a filename and return a secure version of it.
    
    This function works similar to the werkzeug.utils.secure_filename function.
    It returns a filename that can safely be stored on a regular file system and passed
    to os.path.join() without risking directory traversal attacks.
    
    Args:
        filename: The filename to secure
        
    Returns:
        A sanitized filename
    """
    if not filename:
        return 'unnamed_file'
        
    _filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')
    
    # Replace directory separators with underscores
    filename = filename.replace('/', '_')
    filename = filename.replace('\\', '_')
    
    # Strip non-ASCII characters
    filename = _filename_ascii_strip_re.sub('', filename).strip('._')
    
    # Make sure we don't have an empty filename
    if not filename:
        filename = 'unnamed_file'
        
    return filename

def safe_path_join(base_dir: Union[str, Path], *paths) -> Path:
    """
    Safely join paths to prevent directory traversal attacks.
    
    Args:
        base_dir: The base directory that should contain the final path
        *paths: Path components to join
        
    Returns:
        A safe, absolute path that is guaranteed to be within base_dir
        
    Raises:
        ValueError: If the resulting path would be outside the base directory
    """
    # Resolve the base directory to an absolute path
    base_path = Path(base_dir).resolve()
    
    # Join and resolve the new path
    joined_path = base_path.joinpath(*paths).resolve()
    
    # Ensure the joined path starts with the base path
    if not str(joined_path).startswith(str(base_path)):
        logger.error(f"Path traversal attempt detected: {joined_path} is outside {base_path}")
        raise ValueError(f"Path {joined_path} is outside base directory {base_path}")
        
    return joined_path

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
        safe_path_join(base_dir, Path(path).name)
        return True
    except ValueError:
        return False 