import os
import re
import uuid
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status


def validate_url(url: str) -> bool:
    """
    Validate if a given URL is well-formed and points to an allowed domain.

    Args:
        url: The URL to validate

    Returns:
        bool: True if the URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False


def validate_file_type(
    content_type: str, allowed_types: Optional[list[str]] = None
) -> bool:
    """
    Validate if a given content type is allowed.

    Args:
        content_type: The MIME type to validate
        allowed_types: List of allowed MIME types. If None, defaults to PDF and DOCX

    Returns:
        bool: True if the content type is allowed, False otherwise
    """
    if not allowed_types:
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]

    return content_type.lower() in [t.lower() for t in allowed_types]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal and ensure safe characters.

    Args:
        filename: The filename to sanitize

    Returns:
        str: The sanitized filename
    """
    # Remove any directory components
    filename = filename.replace("\\", "/").split("/")[-1]

    # Replace potentially dangerous characters
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

    # Ensure the filename isn't too long
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[: 255 - len(ext)] + ext

    return filename


def validate_file_size(size: int, max_size: Optional[int] = None) -> bool:
    """
    Validate if a file size is within allowed limits.

    Args:
        size: The file size in bytes
        max_size: Maximum allowed size in bytes. If None, defaults to 10MB

    Returns:
        bool: True if the file size is allowed, False otherwise
    """
    if max_size is None:
        max_size = 10 * 1024 * 1024  # 10MB

    return 0 < size <= max_size


def validate_object_id(id_str: Optional[str]):
    """
    Validate that the provided string is a valid UUID.

    Args:
        id_str: String to validate as UUID

    Raises:
        HTTPException: If the string is not a valid UUID
    """
    if id_str is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing ID parameter"
        )

    try:
        # Try to parse as UUID
        uuid.UUID(id_str)
    except ValueError:
        # Check if it's a valid alternative format (using regex)
        if not re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            id_str,
            re.I,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ID format: {id_str}. Must be a valid UUID.",
            )


def is_valid_object_id(id_str: Optional[str]) -> bool:
    """
    Check if the provided string is a valid UUID.

    Args:
        id_str: String to check

    Returns:
        True if valid, False otherwise
    """
    if id_str is None:
        return False

    try:
        uuid.UUID(id_str)
        return True
    except ValueError:
        # Check if it's a valid alternative format
        return bool(
            re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                id_str,
                re.I,
            )
        )
