"""
API endpoints for chunked file uploads.
"""

import json
import logging
import math
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path, PurePath
from typing import Any, Dict, Optional, Set

from config import settings
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from utils.error_handler import ErrorHandler, raise_error
from utils.supabase_helper import supabase_client_context

router = APIRouter()
logger = logging.getLogger(__name__)

# Directory for storing temporary chunks during upload
CHUNKS_DIR = Path(settings.UPLOAD_DIR) / "chunks"
CHUNKS_DIR.mkdir(exist_ok=True, parents=True)

# Define default chunk size if not in settings
CHUNK_SIZE = getattr(settings, "CHUNK_SIZE", 5 * 1024 * 1024)  # 5MB default

# Maximum upload size limit (1GB by default)
MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 1024 * 1024 * 1024)

# Allowed file types (MIME types)
ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png",
    "image/gif",
}

# Dictionary to track upload metadata
upload_metadata: Dict[str, Dict[str, Any]] = {}

def is_valid_filename(filename: str) -> bool:
    """
    Validate if a filename is safe to use.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not filename or len(filename) > 255:
        return False
        
    # Disallow paths with directory traversal
    if '/' in filename or '\\' in filename:
        return False
        
    # Check for common invalid characters
    invalid_chars = '<>:"|?*\x00-\x1F'
    if any(char in filename for char in invalid_chars):
        return False
        
    return True
    
def is_allowed_file_type(mime_type: str) -> bool:
    """
    Check if a file type is allowed based on its MIME type.
    
    Args:
        mime_type: MIME type to check
        
    Returns:
        True if allowed, False otherwise
    """
    return mime_type in ALLOWED_MIME_TYPES

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to ensure it's safe for storage.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    # Get just the filename without any path components
    clean_name = PurePath(filename).name

    # Replace any potentially dangerous characters
    clean_name = re.sub(r'[\\/:*?"<>|\x00-\x1F]', "_", clean_name)

    # Limit length
    if len(clean_name) > 255:
        name_parts = clean_name.split(".")
        extension = name_parts[-1] if len(name_parts) > 1 else ""
        base_name = ".".join(name_parts[:-1]) if len(name_parts) > 1 else name_parts[0]

        # Truncate the base name to fit within the 255 character limit with extension
        max_base_len = 255 - len(extension) - 1  # -1 for the dot
        base_name = base_name[:max_base_len]

        clean_name = f"{base_name}.{extension}" if extension else base_name

    return clean_name


# Security utility functions to prevent path traversal
def validate_upload_id(upload_id: str) -> bool:
    """
    Validate that an upload ID follows the expected format to prevent path traversal.
    Only alphanumeric characters and hyphens are allowed.
    
    Args:
        upload_id: The upload ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Strict validation: only allow alphanumeric characters and hyphens
    return bool(re.match(r'^[a-zA-Z0-9\-_]+$', upload_id))


def calculate_chunk_size(file_size: int) -> int:
    """
    Calculate optimal chunk size based on file size.
    
    Args:
        file_size: Size of the file in bytes
        
    Returns:
        Appropriate chunk size in bytes
    """
    # Default chunk size
    base_chunk_size = 5 * 1024 * 1024  # 5MB
    
    # For small files, use smaller chunks
    if file_size < 10 * 1024 * 1024:  # Less than 10MB
        return min(base_chunk_size, max(1 * 1024 * 1024, file_size // 5))  # At least 1MB
        
    # For medium files
    if file_size < 100 * 1024 * 1024:  # Less than 100MB
        return base_chunk_size
        
    # For larger files, use larger chunks (but not too large)
    return min(10 * 1024 * 1024, max(base_chunk_size, file_size // 20))  # Max 10MB


def get_safe_chunk_path(upload_id: str, chunk_index: Optional[int] = None) -> Optional[Path]:
    """
    Generate a safe path for chunk files.
    
    Args:
        upload_id: The ID of the upload
        chunk_index: Optional index of the chunk. If None, returns the upload directory path
    
    Returns:
        Path object for the chunk file or upload directory if valid, None if invalid
    """
    # Validate the upload ID to prevent path traversal
    if not validate_upload_id(upload_id):
        logging.error(f"Invalid upload ID format: {upload_id}")
        return None
    
    upload_dir = CHUNKS_DIR / upload_id
    
    if chunk_index is None:
        # Return the upload directory path
        return upload_dir
    
    # Validate the chunk index
    if not isinstance(chunk_index, int) or chunk_index < 0:
        logging.error(f"Invalid chunk index: {chunk_index}")
        return None
    
    # Return path to specific chunk file
    return upload_dir / f"{chunk_index}"


def safely_open_file(path: Optional[Path], mode: str = "r") -> Optional[Any]:
    """
    Safely open a file within the allowed directory.
    
    Args:
        path: Path object for the file or None
        mode: File mode ('r', 'w', etc.)
    
    Returns:
        File object if path is valid and within allowed directory, None otherwise
    """
    if path is None:
        logging.error("Cannot open file: path is None")
        return None
        
    try:
        # Ensure the path is within the allowed directory
        if not CHUNKS_DIR or not path.is_relative_to(CHUNKS_DIR):
            logging.error(f"Security violation: File path not in allowed directory: {path}")
            return None
            
        # Open the file
        return open(path, mode)
    except Exception as e:
        logging.error(f"Error opening file {path}: {str(e)}")
        return None


@router.post("/initialize")
async def initialize_chunked_upload(
    request: Request,
    filename: str = Form(...),
    fileSize: int = Form(...),
    mimeType: str = Form(...),
    uploadId: Optional[str] = Form(None),
    reportId: Optional[str] = Form(None),
):
    """
    Initialize a new chunked upload session.

    Args:
        filename: Name of the file being uploaded
        fileSize: Total size of the file in bytes
        mimeType: MIME type of the file
        uploadId: Optional existing upload ID for resuming
        reportId: Optional report ID to associate this upload with

    Returns:
        JSON response with upload information
    """
    try:
        # Validate file size
        if fileSize <= 0:
            raise_error(
                "validation",
                message="Invalid file size",
                detail="File size must be greater than 0",
            )

        if fileSize > MAX_UPLOAD_SIZE:
            raise_error(
                "validation",
                message="File too large",
                detail=f"Maximum file size is {MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
            )

        # Validate filename
        if not is_valid_filename(filename):
            raise_error(
                "validation",
                message="Invalid filename",
                detail="Filename contains invalid characters",
            )

        # Sanitize filename
        safe_filename = sanitize_filename(filename)

        # Validate file type
        if not is_allowed_file_type(mimeType):
            raise_error(
                "validation",
                message="File type not allowed",
                detail=f"File type {mimeType} is not allowed",
            )

        # Generate a new upload ID if not provided
        upload_id = uploadId or f"upload_{uuid.uuid4()}"

        # Validate upload ID format to prevent path traversal
        if not validate_upload_id(upload_id):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format",
            )

        # Create upload directory using safe path handling
        safe_upload_dir = get_safe_chunk_path(upload_id)
        if not safe_upload_dir:
            raise_error(
                "security_violation",
                message="Invalid upload path",
                detail="Could not create a safe upload directory path",
            )
            
        # Only try to create directory if we have a valid path
        safe_upload_dir.mkdir(exist_ok=True, parents=True)
        
        # Create metadata file
        metadata_path = safe_upload_dir / "metadata.json"
        
        # Additional verification that metadata path is safe
        if not metadata_path or not CHUNKS_DIR or not metadata_path.is_relative_to(CHUNKS_DIR):
            raise_error(
                "security_violation",
                message="Invalid metadata path",
                detail="Path validation failed for metadata file",
            )
            
        # Calculate optimal chunk size
        chunk_size = calculate_chunk_size(fileSize)
        total_chunks = math.ceil(fileSize / chunk_size)

        # Check if this is a new upload or resuming an existing one
        metadata = {}
        if metadata_path.exists():
            # Resuming an existing upload
            f = safely_open_file(metadata_path, "r")
            if f is None:
                raise_error(
                    "security_violation", 
                    message="Cannot read metadata file",
                    detail="Path validation failed for metadata file",
                )
            try:
                metadata = json.load(f)
                f.close()
            except Exception as e:
                logging.error(f"Error reading metadata file: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Error reading metadata file"
                )

            # Update the metadata if needed
            metadata["fileSize"] = fileSize
            metadata["mimeType"] = mimeType
            metadata["filename"] = safe_filename
            if reportId:
                metadata["reportId"] = reportId
        else:
            # New upload
            metadata = {
                "uploadId": upload_id,
                "filename": safe_filename,
                "fileSize": fileSize,
                "mimeType": mimeType,
                "reportId": reportId,
                "chunkSize": chunk_size,
                "totalChunks": total_chunks,
                "uploadedChunks": [],
                "createdAt": str(datetime.now()),
                "status": "initialized",
            }

        # Store metadata
        f = safely_open_file(metadata_path, "w")
        if f is None:
            raise_error(
                "security_violation",
                message="Cannot write metadata file",
                detail="Path validation failed for metadata file",
            )
        try:
            json.dump(metadata, f)
            f.close()
        except Exception as e:
            logging.error(f"Error writing metadata file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error writing metadata file"
            )

        # Check which chunks have already been uploaded
        if not safe_upload_dir:
            raise_error(
                "security_violation",
                message="Invalid upload path",
                detail="Could not validate upload directory path",
            )
            
        # Only iterate over files if directory exists
        uploaded_chunks = []
        if safe_upload_dir is not None and safe_upload_dir.exists():
            chunk_files = list(safe_upload_dir.glob("chunk_*.bin"))
            
            for chunk_file in chunk_files:
                try:
                    chunk_index = int(chunk_file.stem.split("_")[1])
                    uploaded_chunks.append(chunk_index)
                except (ValueError, IndexError):
                    continue

        # Update metadata with uploaded chunks
        metadata["uploadedChunks"] = sorted(uploaded_chunks)

        f = safely_open_file(metadata_path, "w")
        if f is None:
            raise_error(
                "security_violation", 
                message="Cannot update metadata file",
                detail="Path validation failed for metadata file",
            )
        try:
            json.dump(metadata, f)
            f.close()
        except Exception as e:
            logging.error(f"Error updating metadata file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error updating metadata file"
            )

        # Return upload information
        return {
            "uploadId": upload_id,
            "chunkSize": chunk_size,
            "totalChunks": total_chunks,
            "uploadedChunks": metadata["uploadedChunks"],
            "resumable": True,
        }
    except Exception as e:
        logger.exception("Failed to initialize chunked upload")
        if isinstance(e, HTTPException):
            raise e

        ErrorHandler.raise_error(
            "internal",
            message="Failed to initialize chunked upload",
            detail=str(e),
            context={"filename": filename, "fileSize": fileSize},
        )


@router.post("/chunk")
async def upload_chunk(
    request: Request,
    uploadId: str = Form(...),
    chunkIndex: int = Form(...),
    start: int = Form(...),
    end: int = Form(...),
    chunk: UploadFile = File(...),
):
    """
    Upload a single chunk of a file.

    Args:
        uploadId: ID of the upload session
        chunkIndex: Index of the chunk (0-based)
        start: Start byte position of the chunk
        end: End byte position of the chunk
        chunk: The chunk data

    Returns:
        JSON response with chunk upload status
    """
    try:
        # Validate upload ID format to prevent path traversal
        if not validate_upload_id(uploadId):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format",
            )

        # Get safe path for upload directory
        safe_upload_dir = get_safe_chunk_path(uploadId)
        if not safe_upload_dir or not safe_upload_dir.exists():
            raise_error(
                "not_found",
                message="Upload session not found",
                detail=f"No upload session found with ID {uploadId}",
            )

        # Get safe path for metadata file
        metadata_path = safe_upload_dir / "metadata.json"
        # Additional verification that metadata file is in the correct location
        if not safe_upload_dir or not metadata_path or not metadata_path.is_relative_to(safe_upload_dir) or metadata_path.name != "metadata.json":
            raise_error(
                "security_violation",
                message="Invalid metadata path",
                detail="Attempted to access file outside of upload directory",
            )
            
        if not metadata_path.exists():
            raise_error(
                "not_found",
                message="Upload metadata not found",
                detail=f"Metadata not found for upload {uploadId}",
            )

        # Load metadata
        f = safely_open_file(metadata_path, "r")
        if f is None:
            raise_error(
                "security_violation", 
                message="Cannot read metadata file",
                detail="Path validation failed for metadata file",
            )
        try:
            metadata = json.load(f)
            f.close()
        except Exception as e:
            logging.error(f"Error reading metadata file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error reading metadata file"
            )

        # Validate chunk index
        if chunkIndex < 0 or chunkIndex >= metadata["totalChunks"]:
            raise_error(
                "validation",
                message="Invalid chunk index",
                detail=f"Chunk index {chunkIndex} is out of range (0-{metadata['totalChunks']-1})",
            )

        # Validate start and end positions
        if start < 0 or end <= start or end > metadata["fileSize"]:
            raise_error(
                "validation",
                message="Invalid chunk range",
                detail=f"Invalid chunk range (start={start}, end={end}, fileSize={metadata['fileSize']})",
            )

        # Validate chunk size
        expected_size = min(metadata["chunkSize"], metadata["fileSize"] - start)

        # Save the chunk using a safe path
        chunk_filename = f"chunk_{chunkIndex}.bin"
        # Ensure the filename is safe
        if not re.match(r"^chunk_\d+\.bin$", chunk_filename):
            raise_error(
                "validation",
                message="Invalid chunk filename",
                detail="Chunk filename must be in the correct format",
            )

        chunk_path = safe_upload_dir / chunk_filename
        chunk_data = await chunk.read()
        
        # Validate chunk size against expected size
        actual_size = len(chunk_data)
        if actual_size > expected_size * 1.1:  # Allow 10% margin for safety
            raise_error(
                "validation",
                message="Chunk too large",
                detail=f"Chunk size ({actual_size} bytes) exceeds expected size ({expected_size} bytes)",
            )
            
        # Save the chunk
        f = safely_open_file(chunk_path, "wb")
        if f is None:
            raise_error(
                "security_violation",
                message="Cannot save chunk file",
                detail="Path validation failed for chunk file",
            )
        try:
            f.write(chunk_data)
            f.close()
        except Exception as e:
            logging.error(f"Error writing chunk file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error writing chunk file"
            )

        # Verify file was written
        if not chunk_path.exists():
            raise_error(
                "file_operation",
                message="Failed to save chunk",
                detail="Chunk file could not be saved",
            )
        
        actual_size = chunk_path.stat().st_size
        if actual_size != expected_size:
            # This is not a fatal error, but log it
            logger.warning(
                f"Chunk size mismatch: expected {expected_size} bytes, got {actual_size} bytes"
            )

        # Update metadata
        if chunkIndex not in metadata["uploadedChunks"]:
            metadata["uploadedChunks"].append(chunkIndex)
            metadata["uploadedChunks"].sort()

        with safely_open_file(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Check if upload is complete
        is_complete = len(metadata["uploadedChunks"]) == metadata["totalChunks"]

        return {
            "chunkIndex": chunkIndex,
            "received": actual_size,
            "start": start,
            "end": end,
            "isComplete": is_complete,
        }
    except Exception as e:
        logger.exception(f"Failed to upload chunk {chunkIndex}")
        if isinstance(e, HTTPException):
            raise e

        ErrorHandler.raise_error(
            "internal",
            message="Failed to upload chunk",
            detail=str(e),
            context={"uploadId": uploadId, "chunkIndex": chunkIndex},
        )


@router.post("/finalize")
async def finalize_chunked_upload(
    request: Request,
    uploadId: str = Form(...),
    filename: str = Form(...),
    reportId: Optional[str] = Form(None),
):
    """
    Finalize a chunked upload, combining all chunks into a single file.

    Args:
        uploadId: ID of the upload session
        filename: Name of the final file
        reportId: Optional report ID to associate this upload with

    Returns:
        JSON response with finalized file information
    """
    # Validate uploadId (should only contain alphanumeric characters and hyphens)
    if not validate_upload_id(uploadId):
        raise_error(
            "validation",
            message="Invalid upload ID format",
            detail="Upload ID contains invalid characters"
        )
        
    try:
        # Get safe path for upload directory
        safe_upload_dir = get_safe_chunk_path(uploadId)
        if not safe_upload_dir or not safe_upload_dir.exists():
            raise_error(
                "not_found",
                message="Upload session not found",
                detail=f"No upload session found with ID {uploadId}",
            )

        # Get safe path for metadata file
        metadata_path = safe_upload_dir / "metadata.json"
        # Additional verification that metadata file is in the correct location
        if not safe_upload_dir or not metadata_path or not metadata_path.is_relative_to(safe_upload_dir) or metadata_path.name != "metadata.json":
            raise_error(
                "security_violation",
                message="Invalid metadata path",
                detail="Attempted to access file outside of upload directory",
            )
            
        if not metadata_path.exists():
            raise_error(
                "not_found",
                message="Upload metadata not found",
                detail=f"Metadata not found for upload {uploadId}",
            )

        # Load metadata
        f = safely_open_file(metadata_path, "r")
        if f is None:
            raise_error(
                "security_violation", 
                message="Cannot read metadata file",
                detail="Path validation failed for metadata file",
            )
        try:
            metadata = json.load(f)
            f.close()
        except Exception as e:
            logging.error(f"Error reading metadata file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error reading metadata file"
            )

        # Check if upload is complete
        if len(metadata["uploadedChunks"]) != metadata["totalChunks"]:
            missing_chunks = set(range(metadata["totalChunks"])) - set(
                metadata["uploadedChunks"]
            )
            raise_error(
                "validation",
                message="Upload is incomplete",
                detail=f"Missing chunks: {list(missing_chunks)[:10]}...",
            )

        # Validate the file type based on metadata
        if not is_allowed_file_type(metadata["mimeType"]):
            raise_error(
                "validation",
                message="File type not allowed",
                detail=f"File type {metadata['mimeType']} is not allowed",
            )

        # Create a final file path with proper sanitization
        report_id = reportId or metadata.get("reportId") or str(uuid.uuid4())

        # Validate report ID format
        if not re.match(r"^[0-9a-f\-]+$", report_id):
            # Generate a new valid UUID if the report ID is invalid
            logger.warning(
                f"Invalid report ID format: {report_id}, generating new UUID"
            )
            report_id = str(uuid.uuid4())

        # Use safe path joining
        report_dir = Path(settings.UPLOAD_DIR) / report_id
        report_dir.mkdir(parents=True, exist_ok=True)

        output_path = report_dir / filename

        # First combine chunks into a temporary file for virus scanning
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

            # Combine chunks
            file_size = 0
            for i in range(metadata["totalChunks"]):
                chunk_path = safe_upload_dir / f"chunk_{i}.bin"
                if not chunk_path.exists():
                    raise_error(
                        "internal",
                        message="Chunk file missing",
                        detail=f"Chunk {i} is missing from upload directory",
                    )
                
                # Additional safety check for the chunk path
                if not chunk_path.is_relative_to(safe_upload_dir):
                    raise_error(
                        "security_violation",
                        message="Invalid chunk path",
                        detail=f"Chunk {i} path is outside the upload directory",
                    )

                with safely_open_file(chunk_path, "rb") as chunk_file:
                    if chunk_file is None:
                        raise_error(
                            "security_violation",
                            message="Cannot read chunk file",
                            detail=f"Path validation failed for chunk {i}",
                        )
                    chunk_data = chunk_file.read()
                    temp_file.write(chunk_data)
                    file_size += len(chunk_data)

        # Verify file size against metadata
        if file_size != metadata["fileSize"]:
            logger.warning(
                f"Final file size mismatch: expected {metadata['fileSize']} bytes, got {file_size} bytes"
            )

        # TODO: Add virus scanning here
        # scan_result = scan_file(temp_path)
        # if not scan_result.is_clean:
        #     os.unlink(temp_path)
        #     raise_error(
        #         "validation",
        #         message="File contains malware",
        #         detail=f"Virus scan detected: {scan_result.threat_name}"
        #     )

        # Copy from temp file to final location
        shutil.copy2(temp_path, output_path)

        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file: {str(e)}")

        # Update metadata
        metadata["status"] = "completed"
        metadata["finalPath"] = str(output_path)
        metadata["finalSize"] = file_size

        with safely_open_file(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Store file information in Supabase if available
        file_info = {
            "file_id": str(uuid.uuid4()),
            "report_id": report_id,
            "filename": filename,
            "file_path": str(output_path),
            "file_type": metadata["mimeType"],
            "file_size": file_size,
        }

        try:
            # Store file info in Supabase
            with supabase_client_context() as supabase:
                result = supabase.table("files").insert(file_info).execute()

                if hasattr(result, "error") and result.error:
                    logger.error(f"Error storing file info in Supabase: {result.error}")
        except Exception as e:
            logger.error(f"Error storing file info in Supabase: {str(e)}")

        # Return finalized file information
        return {
            "success": True,
            "fileId": file_info["file_id"],
            "reportId": report_id,
            "filename": filename,
            "size": file_size,
            "mimeType": metadata["mimeType"],
            "path": str(output_path),
            "url": f"/files/{report_id}/{filename}",
        }
    except Exception as e:
        logger.exception("Failed to finalize upload")
        if isinstance(e, HTTPException):
            raise e

        ErrorHandler.raise_error(
            "internal",
            message="Failed to finalize upload",
            detail=str(e),
            context={"uploadId": uploadId, "filename": filename},
        )
    finally:
        # Schedule cleanup of chunks
        # In a production environment, this should be handled by a background job
        # For now, let's do a simple cleanup
        try:
            # Don't delete immediately to allow for potential error recovery
            # Just mark for cleanup in metadata
            if metadata_path.exists():
                with safely_open_file(metadata_path, "r") as f:
                    metadata = json.load(f)

                metadata["pendingCleanup"] = True

                with safely_open_file(metadata_path, "w") as f:
                    json.dump(metadata, f)
        except Exception as e:
            logger.error(f"Error marking chunks for cleanup: {str(e)}")


@router.post("/cancel")
async def cancel_chunked_upload(request: Request, uploadId: str = Form(...)):
    """
    Cancel a chunked upload and delete all uploaded chunks.

    Args:
        uploadId: ID of the upload session

    Returns:
        JSON response with cancellation status
    """
    try:
        # Validate upload ID format to prevent path traversal
        if not validate_upload_id(uploadId):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format",
            )

        # Get safe path for upload directory
        safe_upload_dir = get_safe_chunk_path(uploadId)
        if not safe_upload_dir or not safe_upload_dir.exists():
            return {
                "success": True,
                "message": "Upload was already cancelled or does not exist",
            }

        # Clean up the upload directory securely
        try:
            # Additional verification that the directory is inside the CHUNKS_DIR
            if not safe_upload_dir.is_relative_to(CHUNKS_DIR):
                raise_error(
                    "security_violation",
                    message="Invalid upload directory",
                    detail="Upload directory is outside the chunks directory",
                )

            shutil.rmtree(safe_upload_dir)
        except Exception as e:
            logger.error(f"Error removing upload directory: {str(e)}")
            raise

        return {"success": True, "message": "Upload cancelled successfully"}
    except Exception as e:
        logger.exception("Failed to cancel upload")
        if isinstance(e, HTTPException):
            raise e

        ErrorHandler.raise_error(
            "internal",
            message="Failed to cancel upload",
            detail=str(e),
            context={"uploadId": uploadId},
        )
