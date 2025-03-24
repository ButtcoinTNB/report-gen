"""
API endpoints for chunked file uploads.
"""

import os
import uuid
import tempfile
import json
import shutil
import re
import mimetypes
from typing import List, Dict, Optional, Any, Set
from fastapi import APIRouter, UploadFile, File, Form, Header, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from utils.error_handler import raise_error, ErrorHandler
from utils.file_utils import safe_path_join, get_mime_type
from utils.supabase_helper import supabase_client_context
from pathlib import Path, PurePath
from config import settings
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Directory for storing temporary chunks during upload
CHUNKS_DIR = Path("uploads/chunks")
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

# Define default chunk size if not in settings
CHUNK_SIZE = getattr(settings, 'CHUNK_SIZE', 5 * 1024 * 1024)  # 5MB default

# Maximum upload size limit (1GB by default)
MAX_UPLOAD_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 1024 * 1024 * 1024)

# Allowed file types (MIME types)
ALLOWED_MIME_TYPES: Set[str] = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'image/jpeg',
    'image/png',
    'image/gif'
}

# Dictionary to track upload metadata
upload_metadata: Dict[str, Dict[str, Any]] = {}

def is_valid_filename(filename: str) -> bool:
    """
    Validate that a filename is safe and doesn't contain path traversal characters.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if the filename is valid, False otherwise
    """
    # Disallow directory traversal and control characters
    if re.search(r'[\\/:*?"<>|\x00-\x1F]', filename) or '..' in filename:
        return False
    
    # Ensure the filename isn't too long
    if len(filename) > 255:
        return False
        
    return True

def is_allowed_file_type(mimetype: str) -> bool:
    """
    Check if a file type is allowed.
    
    Args:
        mimetype: The MIME type to check
        
    Returns:
        True if the file type is allowed, False otherwise
    """
    return mimetype in ALLOWED_MIME_TYPES

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
    clean_name = re.sub(r'[\\/:*?"<>|\x00-\x1F]', '_', clean_name)
    
    # Limit length
    if len(clean_name) > 255:
        name_parts = clean_name.split('.')
        extension = name_parts[-1] if len(name_parts) > 1 else ''
        base_name = '.'.join(name_parts[:-1]) if len(name_parts) > 1 else name_parts[0]
        
        # Truncate the base name to fit within the 255 character limit with extension
        max_base_len = 255 - len(extension) - 1  # -1 for the dot
        base_name = base_name[:max_base_len]
        
        clean_name = f"{base_name}.{extension}" if extension else base_name
    
    return clean_name

@router.post("/initialize")
async def initialize_chunked_upload(
    request: Request,
    filename: str = Form(...),
    fileSize: int = Form(...),
    mimeType: str = Form(...),
    uploadId: Optional[str] = Form(None),
    reportId: Optional[str] = Form(None)
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
                detail="File size must be greater than 0"
            )
            
        if fileSize > MAX_UPLOAD_SIZE:
            raise_error(
                "validation",
                message="File too large",
                detail=f"Maximum file size is {MAX_UPLOAD_SIZE / (1024 * 1024)}MB"
            )
        
        # Validate filename
        if not is_valid_filename(filename):
            raise_error(
                "validation",
                message="Invalid filename",
                detail="Filename contains invalid characters"
            )
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Validate file type
        if not is_allowed_file_type(mimeType):
            raise_error(
                "validation",
                message="File type not allowed",
                detail=f"File type {mimeType} is not allowed"
            )
        
        # Generate a new upload ID if not provided
        upload_id = uploadId or f"upload_{uuid.uuid4()}"
        
        # Validate upload ID format to prevent path traversal
        if not re.match(r'^upload_[0-9a-f\-]+$', upload_id):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format"
            )
        
        # Create a directory for storing chunks
        upload_dir = CHUNKS_DIR / upload_id
        upload_dir.mkdir(exist_ok=True)
        
        # Check if this is a new upload or resuming an existing one
        metadata_path = upload_dir / "metadata.json"
        
        if metadata_path.exists():
            # Resuming an existing upload
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                
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
                "chunkSize": CHUNK_SIZE,
                "totalChunks": (fileSize + CHUNK_SIZE - 1) // CHUNK_SIZE,
                "uploadedChunks": [],
                "createdAt": str(datetime.now()),
                "status": "initialized"
            }
        
        # Store metadata
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
            
        # Check which chunks have already been uploaded
        upload_dir = CHUNKS_DIR / upload_id
        chunk_files = list(upload_dir.glob("chunk_*.bin"))
        
        uploaded_chunks = []
        for chunk_file in chunk_files:
            try:
                chunk_index = int(chunk_file.stem.split("_")[1])
                uploaded_chunks.append(chunk_index)
            except (ValueError, IndexError):
                continue
                
        # Update metadata with uploaded chunks
        metadata["uploadedChunks"] = sorted(uploaded_chunks)
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
            
        # Return upload information
        return {
            "uploadId": upload_id,
            "chunkSize": CHUNK_SIZE,
            "totalChunks": metadata["totalChunks"],
            "uploadedChunks": metadata["uploadedChunks"],
            "resumable": True
        }
    except Exception as e:
        logger.exception("Failed to initialize chunked upload")
        if isinstance(e, HTTPException):
            raise e
            
        ErrorHandler.raise_error(
            "internal",
            message="Failed to initialize chunked upload",
            detail=str(e),
            context={"filename": filename, "fileSize": fileSize}
        )

@router.post("/chunk")
async def upload_chunk(
    request: Request,
    uploadId: str = Form(...),
    chunkIndex: int = Form(...),
    start: int = Form(...),
    end: int = Form(...),
    chunk: UploadFile = File(...)
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
        if not re.match(r'^upload_[0-9a-f\-]+$', uploadId):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format"
            )
            
        # Verify upload session exists
        upload_dir = CHUNKS_DIR / uploadId
        if not upload_dir.exists():
            raise_error(
                "not_found",
                message="Upload session not found",
                detail=f"No upload session found with ID {uploadId}"
            )
            
        # Verify metadata exists
        metadata_path = upload_dir / "metadata.json"
        if not metadata_path.exists():
            raise_error(
                "not_found",
                message="Upload metadata not found",
                detail=f"Metadata not found for upload {uploadId}"
            )
            
        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            
        # Validate chunk index
        if chunkIndex < 0 or chunkIndex >= metadata["totalChunks"]:
            raise_error(
                "validation",
                message="Invalid chunk index",
                detail=f"Chunk index {chunkIndex} is out of range (0-{metadata['totalChunks']-1})"
            )
            
        # Validate start and end positions
        if start < 0 or end <= start or end > metadata["fileSize"]:
            raise_error(
                "validation",
                message="Invalid chunk range",
                detail=f"Invalid chunk range (start={start}, end={end}, fileSize={metadata['fileSize']})"
            )
            
        # Validate chunk size
        expected_size = min(metadata["chunkSize"], metadata["fileSize"] - start)
        
        # Save the chunk using a safe path
        chunk_filename = f"chunk_{chunkIndex}.bin"
        # Ensure the filename is safe
        if not re.match(r'^chunk_\d+\.bin$', chunk_filename):
            raise_error(
                "validation",
                message="Invalid chunk filename",
                detail="Chunk filename must be in the correct format"
            )
            
        chunk_path = upload_dir / chunk_filename
        with open(chunk_path, "wb") as f:
            chunk_data = await chunk.read()
            
            # Validate chunk size against expected size
            actual_size = len(chunk_data)
            if actual_size > expected_size * 1.1:  # Allow 10% margin for safety
                raise_error(
                    "validation",
                    message="Chunk too large",
                    detail=f"Chunk size ({actual_size} bytes) exceeds expected size ({expected_size} bytes)"
                )
                
            f.write(chunk_data)
            
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
            
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
            
        # Check if upload is complete
        is_complete = len(metadata["uploadedChunks"]) == metadata["totalChunks"]
        
        return {
            "chunkIndex": chunkIndex,
            "received": actual_size,
            "start": start,
            "end": end,
            "isComplete": is_complete
        }
    except Exception as e:
        logger.exception(f"Failed to upload chunk {chunkIndex}")
        if isinstance(e, HTTPException):
            raise e
            
        ErrorHandler.raise_error(
            "internal",
            message="Failed to upload chunk",
            detail=str(e),
            context={"uploadId": uploadId, "chunkIndex": chunkIndex}
        )

@router.post("/finalize")
async def finalize_chunked_upload(
    request: Request,
    uploadId: str = Form(...),
    filename: str = Form(...),
    reportId: Optional[str] = Form(None)
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
    try:
        # Validate upload ID format to prevent path traversal
        if not re.match(r'^upload_[0-9a-f\-]+$', uploadId):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format"
            )
            
        # Validate filename
        if not is_valid_filename(filename):
            raise_error(
                "validation",
                message="Invalid filename",
                detail=f"Filename contains invalid characters: {filename}"
            )
            
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Verify upload session exists
        upload_dir = CHUNKS_DIR / uploadId
        if not upload_dir.exists():
            raise_error(
                "not_found",
                message="Upload session not found",
                detail=f"No upload session found with ID {uploadId}"
            )
            
        # Verify metadata exists
        metadata_path = upload_dir / "metadata.json"
        if not metadata_path.exists():
            raise_error(
                "not_found",
                message="Upload metadata not found",
                detail=f"Metadata not found for upload {uploadId}"
            )
            
        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            
        # Check if upload is complete
        if len(metadata["uploadedChunks"]) != metadata["totalChunks"]:
            missing_chunks = set(range(metadata["totalChunks"])) - set(metadata["uploadedChunks"])
            raise_error(
                "validation",
                message="Upload is incomplete",
                detail=f"Missing chunks: {list(missing_chunks)[:10]}..."
            )
        
        # Validate the file type based on metadata
        if not is_allowed_file_type(metadata["mimeType"]):
            raise_error(
                "validation",
                message="File type not allowed",
                detail=f"File type {metadata['mimeType']} is not allowed"
            )
            
        # Create a final file path with proper sanitization
        report_id = reportId or metadata.get("reportId") or str(uuid.uuid4())
        
        # Validate report ID format 
        if not re.match(r'^[0-9a-f\-]+$', report_id):
            # Generate a new valid UUID if the report ID is invalid
            logger.warning(f"Invalid report ID format: {report_id}, generating new UUID")
            report_id = str(uuid.uuid4())
            
        # Use safe path joining
        report_dir = Path(settings.UPLOAD_DIR) / report_id
        report_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = report_dir / safe_filename
        
        # First combine chunks into a temporary file for virus scanning
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            
            # Combine chunks
            file_size = 0
            for i in range(metadata["totalChunks"]):
                chunk_path = upload_dir / f"chunk_{i}.bin"
                if not chunk_path.exists():
                    raise_error(
                        "internal",
                        message="Chunk file missing",
                        detail=f"Chunk {i} is missing from upload directory"
                    )
                    
                with open(chunk_path, "rb") as chunk_file:
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
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
            
        # Store file information in Supabase if available
        file_info = {
            "file_id": str(uuid.uuid4()),
            "report_id": report_id,
            "filename": safe_filename,
            "file_path": str(output_path),
            "file_type": metadata["mimeType"],
            "file_size": file_size
        }
        
        try:
            # Store file info in Supabase
            with supabase_client_context() as supabase:
                result = supabase.table("files").insert(file_info).execute()
                
                if hasattr(result, 'error') and result.error:
                    logger.error(f"Error storing file info in Supabase: {result.error}")
        except Exception as e:
            logger.error(f"Error storing file info in Supabase: {str(e)}")
        
        # Return finalized file information
        return {
            "success": True,
            "fileId": file_info["file_id"],
            "reportId": report_id,
            "filename": safe_filename,
            "size": file_size,
            "mimeType": metadata["mimeType"],
            "path": str(output_path),
            "url": f"/files/{report_id}/{safe_filename}"
        }
    except Exception as e:
        logger.exception("Failed to finalize upload")
        if isinstance(e, HTTPException):
            raise e
            
        ErrorHandler.raise_error(
            "internal",
            message="Failed to finalize upload",
            detail=str(e),
            context={"uploadId": uploadId, "filename": filename}
        )
    finally:
        # Schedule cleanup of chunks
        # In a production environment, this should be handled by a background job
        # For now, let's do a simple cleanup
        try:
            # Don't delete immediately to allow for potential error recovery
            # Just mark for cleanup in metadata
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    
                metadata["pendingCleanup"] = True
                
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
        except Exception as e:
            logger.error(f"Error marking chunks for cleanup: {str(e)}")

@router.post("/cancel")
async def cancel_chunked_upload(
    request: Request,
    uploadId: str = Form(...)
):
    """
    Cancel a chunked upload and delete all uploaded chunks.
    
    Args:
        uploadId: ID of the upload session
        
    Returns:
        JSON response with cancellation status
    """
    try:
        # Validate upload ID format to prevent path traversal
        if not re.match(r'^upload_[0-9a-f\-]+$', uploadId):
            raise_error(
                "validation",
                message="Invalid upload ID format",
                detail="Upload ID must be in the correct format"
            )
            
        # Verify upload session exists
        upload_dir = CHUNKS_DIR / uploadId
        if not upload_dir.exists():
            return {
                "success": True,
                "message": "Upload was already cancelled or does not exist"
            }
        
        # Clean up the upload directory securely
        try:
            # First verify this is actually a chunks directory, not some other path
            if not str(upload_dir).startswith(str(CHUNKS_DIR)):
                raise_error(
                    "validation",
                    message="Invalid upload directory",
                    detail="Upload directory is outside the chunks directory"
                )
                
            shutil.rmtree(upload_dir)
        except Exception as e:
            logger.error(f"Error removing upload directory: {str(e)}")
            raise
        
        return {
            "success": True,
            "message": "Upload cancelled successfully"
        }
    except Exception as e:
        logger.exception("Failed to cancel upload")
        if isinstance(e, HTTPException):
            raise e
            
        ErrorHandler.raise_error(
            "internal",
            message="Failed to cancel upload",
            detail=str(e),
            context={"uploadId": uploadId}
        ) 