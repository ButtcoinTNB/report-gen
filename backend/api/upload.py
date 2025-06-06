"""
Upload API endpoints for file uploads
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, cast
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import UUID4, BaseModel
from postgrest import AsyncPostgrestClient

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from api.schemas import APIResponse, UploadQueryResult
    from config import settings
    from models import Template, User
    from services.pdf_extractor import extract_text_from_file
    from services.upload_service import upload_service
    from utils.auth import get_current_user
    from utils.error_handler import api_error_handler, logger
    from utils.exceptions import (
        DatabaseException,
        FileProcessingException,
        InternalServerException,
        ValidationException,
    )
    from utils.file_processor import FileProcessor
    from utils.file_utils import safe_path_join, secure_filename, get_file_type, get_mime_type
    from utils.logger import get_logger
    from utils.supabase_helper import create_supabase_client, supabase_client_context, async_supabase_client_context
    from utils.storage import get_absolute_file_path, get_relative_file_path, validate_file_exists
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from api.schemas import APIResponse, UploadQueryResult
    from config import settings
    from models import Template, User
    from services.pdf_extractor import extract_text_from_file
    from services.upload_service import upload_service
    from utils.auth import get_current_user
    from utils.error_handler import api_error_handler, logger
    from utils.exceptions import (
        DatabaseException,
        FileProcessingException,
        InternalServerException,
        ValidationException,
    )
    from utils.file_processor import FileProcessor
    from utils.file_utils import safe_path_join, secure_filename, get_file_type, get_mime_type
    from utils.logger import get_logger
    from utils.supabase_helper import (
        create_supabase_client,
        supabase_client_context,
        async_supabase_client_context
    )
    from utils.storage import get_absolute_file_path, get_relative_file_path, validate_file_exists

# Create logger
logger = get_logger(__name__)

# Create router
router = APIRouter(tags=["upload"])

# Background tasks queue
background_tasks = {}

T = TypeVar('T')

class UploadResponse(BaseModel):
    """Response model for file upload."""
    uploaded_files: List[UUID4]
    template_id: Optional[UUID4] = None


class ChunkedUploadInit(BaseModel):
    """Request model for initializing a chunked upload"""

    filename: str
    fileSize: int
    fileType: str
    totalChunks: int
    reportId: Optional[str] = None
    templateId: Optional[str] = None


class ChunkUploadComplete(BaseModel):
    """Request model for completing a chunked upload"""

    uploadId: str


# Background task to process an uploaded file
async def process_file_in_background(
    file_path: str, file_metadata: Dict[str, Any], report_id: str
):
    """
    Process an uploaded file in the background
    This includes extracting text and metadata and storing in the database
    """
    try:
        # Convert relative path to absolute for processing
        abs_file_path = get_absolute_file_path(file_path)
        
        # Verify file exists
        if not validate_file_exists(file_path):
            logger.error(f"File not found at path: {file_path}")
            return

        # Get file info using FileProcessor
        file_info = FileProcessor.get_file_info(abs_file_path)
        mime_type = file_info["mime_type"]

        # Extract content if it's a text-based file
        content = None
        if FileProcessor.is_text_file(abs_file_path):
            content = FileProcessor.extract_text(abs_file_path)

        # Update the file record and link to report in a single transaction
        async with async_supabase_client_context() as supabase:
            # Update file content and mime type
            await supabase.table("files").update({
                "content": content,
                "mime_type": mime_type,
                "processed": True
            }).eq("file_id", file_metadata["file_id"]).execute()

            # Get current document_ids from report
            report_data = await supabase.table("reports").select("document_ids").eq("report_id", report_id).execute()

            if report_data.data:
                current_docs = report_data.data[0].get("document_ids", []) or []
                # Only add if not already in list
                if file_metadata["file_id"] not in current_docs:
                    updated_docs = current_docs + [file_metadata["file_id"]]
                    await supabase.table("reports").update({
                        "document_ids": updated_docs
                    }).eq("report_id", report_id).execute()

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        # Log the full error for debugging
        import traceback
        logger.error(f"Full error: {traceback.format_exc()}")


@router.post("/template", response_model=APIResponse[Template], status_code=201)
@api_error_handler
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form("1.0"),
):
    """
    Upload a reference PDF template for formatting future reports

    Args:
        file: PDF template file
        name: Template name
        version: Template version

    Returns:
        Standardized API response with the template details
    """
    # Check file type
    if not file.filename.lower().endswith(".pdf"):
        raise ValidationException(
            message="Only PDF files are accepted",
            details={
                "file_extension": file.filename.split(".")[-1],
                "allowed_extensions": ["pdf"],
            },
        )

    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise ValidationException(
            message=f"File size exceeds the {max_size_mb:.1f} MB limit",
            details={"file_size": file.size, "max_size": settings.MAX_UPLOAD_SIZE},
        )

    async with async_supabase_client_context() as supabase:
        # Store file in Supabase
        logger.info(f"Storing template in Supabase database: {name} - v{version}")

        # Check if template with this name already exists
        existing = (
            await supabase.table("templates").select("*").eq("name", name).execute()
        )

        if existing.data:
            raise ValidationException(
                message="Template with this name already exists",
                details={"template_name": name},
            )

    # Create template record
    template_data = {
        "template_id": str(uuid.uuid4()),
        "name": name,
        "version": version,
        "content": "",  # Will be updated after file processing
        "meta_data": {},
    }

    try:
        template_response = (
            await supabase.table("templates").insert(template_data).execute()
        )
        if not template_response.data:
            raise DatabaseException(
                message="Failed to create template record",
                details={"operation": "insert", "table": "templates"},
            )

        template = template_response.data[0]
        template_id = UUID4(template["template_id"])

        # Create unique filename using template_id
        filename = f"template_{template_id}.pdf"
        file_path = safe_path_join(settings.UPLOAD_DIR, filename)

        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise FileProcessingException(
                message=f"Failed to save template file: {str(e)}",
                details={"file_path": file_path},
            )

        try:
            # Extract content from PDF
            content = extract_text_from_file(file_path)
        except Exception as e:
            raise FileProcessingException(
                message=f"Failed to extract text from template: {str(e)}",
                details={"file_path": file_path},
            )

        # Update template with file info
        await supabase.table("templates").update(
            {"file_path": file_path, "content": content}
        ).eq("template_id", str(template_id)).execute()

        return template
    except Exception as e:
        # If this is not one of our custom exceptions, wrap it
        if not isinstance(
            e, (ValidationException, DatabaseException, FileProcessingException)
        ):
            raise InternalServerException(
                message=f"Error processing template upload: {str(e)}",
                details={"template_name": name},
            )
        raise e


@router.post("/files", status_code=201)
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    report_id: Optional[UUID4] = Form(None),
) -> Dict[str, Any]:
    """Upload multiple files and optionally associate with a report"""
    try:
        # Get client IP from request headers
        client_ip = (
            request.headers.get("x-real-ip")
            or request.headers.get("x-forwarded-for")
            or request.client.host
        )

        uploaded_files = []
        with async_supabase_client_context() as supabase:
            for file in files:
                # Generate file_id
                file_id = uuid.uuid4()

                # Save the file using FileProcessor
                file_data = FileProcessor.save_upload(
                    file.file,
                    settings.UPLOAD_DIR,
                    f"{file_id}_{secure_filename(file.filename)}",
                )
                file_path = file_data["file_path"]

                # Extract content if it's a text-based file
                content = None
                if FileProcessor.is_text_file(file_path):
                    content = FileProcessor.extract_text(file_path)

                # Create file record with client IP in metadata
                file_record = {
                    "file_id": str(file_id),
                    "report_id": str(report_id) if report_id else None,
                    "filename": file.filename,
                    "file_path": file_path,
                    "file_type": file_data["mime_type"],
                    "mime_type": file_data["mime_type"],
                    "file_size": file_data["file_size"],
                    "content": content,
                    "metadata": {
                        "ip_address": client_ip,
                        "upload_time": datetime.now().isoformat(),
                    },
                }

                file_response = (
                    await supabase.table("files").insert(file_record).execute()
                )
                if not file_response.data:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create file record for {file.filename}",
                    )

                uploaded_files.append(file_response.data[0])

        return {
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files,
        }

    except Exception as e:
        # Clean up any files that were created
        for file_info in uploaded_files:
            try:
                if os.path.exists(file_info.get("file_path", "")):
                    os.remove(file_info["file_path"])
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))


class UploadDocumentsResponse(BaseModel):
    """Response model for document upload endpoint"""

    report_id: str
    files: List[Dict[str, Any]]
    template_id: Optional[str] = None


@router.post(
    "/documents", status_code=201, response_model=APIResponse[UploadResponse]
)
@api_error_handler
async def upload_documents(
    files: List[UploadFile] = File(...),
    template_id: Optional[UUID4] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """
    Upload documents for report generation.
    
    Args:
        files: List of files to upload
        template_id: Optional template ID to use for report generation
        current_user: Current authenticated user
        background_tasks: FastAPI background tasks
        
    Returns:
        Dictionary containing uploaded file IDs and template ID
    """
    if not files:
        raise ValidationException(
            message="No files provided",
            details={"files": "At least one file must be uploaded"}
        )

    uploaded_files = []
    try:
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)

        async with async_supabase_client_context() as supabase:
            supabase_client = cast(AsyncPostgrestClient, supabase)
            
            for file in files:
                if not file.filename:
                    continue

                # Generate unique filename
                file_id = uuid.uuid4()
                ext = Path(file.filename).suffix
                unique_filename = f"{file_id}{ext}"
                
                # Save file locally
                file_path = upload_dir / unique_filename
                contents = await file.read()
                
                if len(contents) > 10 * 1024 * 1024:  # 10MB limit
                    raise ValidationException(
                        message="File too large",
                        details={"filename": file.filename, "size": len(contents)}
                    )
                
                with open(file_path, "wb") as f:
                    f.write(contents)
                
                # Create file record
                file_record = FileRecord(
                    file_id=file_id,
                    filename=file.filename,
                    file_path=str(file_path),
                    file_type=get_file_type(file.filename),
                    mime_type=get_mime_type(file.filename),
                    file_size=len(contents),
                    content="",
                    status="uploaded",
                    metadata={
                        "upload_time": datetime.now().isoformat(),
                        "original_name": file.filename,
                        "user_id": str(current_user.id) if current_user else None
                    }
                )

                # Insert file record
                response = await supabase_client.table("files").insert(file_record.model_dump()).execute()
                if not response.data:
                    raise DatabaseException(
                        message="Failed to create file record",
                        details={"filename": file.filename}
                    )

                uploaded_files.append(file_id)

                # Start background processing
                if background_tasks:
                    processor = FileProcessor(file_id=file_id)
                    background_tasks.add_task(processor.process)

        return {
            "uploaded_files": uploaded_files,
            "template_id": template_id
        }

    except Exception as e:
        logger.error(f"Error in upload_documents: {str(e)}")
        raise


@router.post("/document", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    report_id: Optional[UUID4] = Form(None),
    doc_type: str = Form("general"),
):
    """
    Upload a document for report generation.

    Args:
        file: The document file to upload
        report_id: Optional UUID of the report to associate with
        doc_type: Type of document (default: general)

    Returns:
        Upload confirmation with file details
    """
    # Check file type (allow various document formats)
    allowed_extensions = [
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".rtf",
        ".jpg",
        ".jpeg",
        ".png",
    ]

    file_ext = os.path.splitext(file.filename)[1].lower()
    if not any(file_ext.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF, Word, text files and images are accepted",
        )

    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        max_size_gb = settings.MAX_UPLOAD_SIZE / (1024 * 1024 * 1024)
        raise HTTPException(
            status_code=400, detail=f"File size exceeds the {max_size_gb:.2f} GB limit"
        )

    # Create unique filename
    unique_id = str(uuid.uuid4())
    safe_filename = secure_filename(file.filename)
    new_filename = f"{unique_id}_{safe_filename}"

    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = safe_path_join(settings.UPLOAD_DIR, new_filename)

    # Save the file
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # In production, would also save to Supabase Storage

    return {
        "success": True,
        "filename": file.filename,
        "stored_path": file_path,
        "file_type": doc_type,
        "report_id": report_id,
    }


@router.post("/template/docx", status_code=201)
async def upload_template_docx(file: UploadFile = File(...)):
    """
    Upload a DOCX template file that will be used for generating reports.
    Uses the /template/docx endpoint to distinguish from PDF template uploads.

    Args:
        file: The DOCX template file to upload

    Returns:
        Dictionary containing the status and path where the template is stored
    """
    try:
        # Check if the file is a DOCX
        content_type = file.content_type
        if (
            content_type
            != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            raise HTTPException(status_code=400, detail="File must be a DOCX document")

        # Check file size
        if file.size > settings.MAX_UPLOAD_SIZE:
            max_size_gb = settings.MAX_UPLOAD_SIZE / (1024 * 1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds the {max_size_gb:.2f} GB limit",
            )

        # Ensure the reference_reports directory exists
        template_dir = safe_path_join("backend", "reference_reports")
        os.makedirs(template_dir, exist_ok=True)

        # Define the path where the template will be saved
        template_path = safe_path_join(template_dir, "template.docx")

        # Save the file
        with open(template_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "status": "success",
            "message": "Template uploaded successfully",
            "path": template_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template upload failed: {str(e)}")


@router.post("/test-single", status_code=201)
async def test_single_upload(
    files: UploadFile = File(...),
):
    """
    Super simple test endpoint for a single file upload.
    Minimal processing, just checks if we can receive a file.
    Uses 'files' parameter name to match the main endpoint's expectation.
    """
    try:
        # Just print basic file info
        print(f"BASIC TEST: Received file {files.filename}, size: {files.size}")

        # Don't even read the file, just acknowledge receipt
        return {
            "success": True,
            "message": "File received",
            "filename": files.filename,
            "size": files.size,
        }
    except Exception as e:
        print(f"Error in basic test: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/debug-upload")
async def debug_upload(request: Request):
    """
    Special endpoint to debug file upload issues.
    Prints detailed information about the incoming request.
    """
    try:
        print("-------- DEBUG REQUEST INFO --------")
        print(f"Request method: {request.method}")
        print(f"Headers: {request.headers}")

        # Try to get content type and length
        content_type = request.headers.get("content-type", "unknown")
        content_length = request.headers.get("content-length", "unknown")
        print(f"Content-Type: {content_type}")
        print(f"Content-Length: {content_length}")

        # Try to parse body as form data
        form = None
        try:
            form = await request.form()
            print("Form data items:")
            for key, value in form.items():
                print(
                    f"  - Key: {key}, Type: {type(value)}, Class: {value.__class__.__name__}"
                )
                if hasattr(value, "filename"):
                    print(
                        f"     Filename: {value.filename}, Size: {value.size if hasattr(value, 'size') else 'unknown'}"
                    )
        except Exception as form_error:
            print(f"Error parsing form: {str(form_error)}")

        # Read raw body if form parsing fails
        if not form:
            try:
                body = await request.body()
                print(f"Raw body length: {len(body)} bytes")
                print(f"First 100 bytes of body: {body[:100]}")
            except Exception as body_error:
                print(f"Error reading body: {str(body_error)}")

        return {
            "message": "Request debug information logged",
            "content_type": content_type,
            "content_length": content_length,
            "form_keys": [key for key in form.keys()] if form else [],
        }

    except Exception as e:
        print(f"Error in debug endpoint: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


@router.post("/chunked/init", response_model=APIResponse[Dict[str, Any]])
@api_error_handler
async def init_chunked_upload(request: ChunkedUploadInit):
    """
    Initialize a chunked file upload

    This endpoint prepares the server to receive a large file in multiple chunks.
    It creates a unique upload ID and tracking information for the upload.

    Args:
        request: Upload initialization details

    Returns:
        Standardized API response with upload ID and tracking information
    """
    try:
        # Generate a unique ID for this upload
        upload_id = str(uuid.uuid4())

        # Determine upload directory
        upload_dir = settings.UPLOAD_DIR

        # If associated with a report, use that subdirectory
        if request.reportId:
            upload_dir = safe_path_join(settings.UPLOAD_DIR, request.reportId)
            os.makedirs(upload_dir, exist_ok=True)

        # If associated with a template, use template directory
        if request.templateId:
            upload_dir = safe_path_join(settings.TEMPLATES_DIR, request.templateId)
            os.makedirs(upload_dir, exist_ok=True)

        # Initialize the chunked upload using FileProcessor
        FileProcessor.init_chunked_upload(
            upload_id=upload_id,
            filename=request.filename,
            total_chunks=request.totalChunks,
            file_size=request.fileSize,
            mime_type=request.fileType,
            directory=upload_dir,
        )

        return {
            "status": "success",
            "data": {
                "uploadId": upload_id,
                "status": "initialized",
                "chunksReceived": 0,
                "totalChunks": request.totalChunks,
            },
        }
    except Exception as e:
        logger.error(f"Error initializing chunked upload: {str(e)}")
        raise InternalServerException(
            message="Failed to initialize chunked upload", details={"error": str(e)}
        )


@router.post(
    "/chunked/chunk/{upload_id}/{chunk_index}",
    response_model=APIResponse[Dict[str, Any]],
)
@api_error_handler
async def upload_chunk(upload_id: str, chunk_index: int, file: UploadFile = File(...)):
    """
    Upload a chunk of a file

    This endpoint receives a chunk of a file being uploaded in parts.

    Args:
        upload_id: Unique ID for this upload from init_chunked_upload
        chunk_index: Index of this chunk (0-based)
        file: The chunk data

    Returns:
        Standardized API response with updated upload status
    """
    try:
        # Process the chunk using FileProcessor
        upload_info = FileProcessor.save_chunk(
            upload_id=upload_id, chunk_index=chunk_index, chunk_data=file.file
        )

        return {
            "status": "success",
            "data": {
                "uploadId": upload_id,
                "chunkIndex": chunk_index,
                "received": upload_info["received_chunks"],
                "total": upload_info["total_chunks"],
                "status": upload_info["status"],
            },
        }
    except ValueError as e:
        logger.error(f"Invalid chunk upload request: {str(e)}")
        raise ValidationException(
            message=str(e), details={"uploadId": upload_id, "chunkIndex": chunk_index}
        )
    except Exception as e:
        logger.error(
            f"Error uploading chunk {chunk_index} for upload {upload_id}: {str(e)}"
        )
        raise InternalServerException(
            message=f"Failed to save chunk {chunk_index}", details={"error": str(e)}
        )


@router.post("/chunked/complete", response_model=APIResponse[Dict[str, Any]])
@api_error_handler
async def complete_chunked_upload(
    request: ChunkUploadComplete, background_tasks: BackgroundTasks
):
    """
    Complete a chunked file upload

    This endpoint combines all uploaded chunks into a single file and processes it.

    Args:
        request: Upload completion details with upload ID

    Returns:
        Standardized API response with file information
    """
    try:
        upload_id = request.uploadId
        
        # Get upload metadata from Supabase
        async with async_supabase_client_context() as supabase:
            # Get upload status
            upload_info = FileProcessor.get_chunked_upload_status(upload_id)

            if not upload_info:
                raise ValidationException(
                    message=f"Upload {upload_id} not found", details={"uploadId": upload_id}
                )

            # Check if upload is complete
            if (
                upload_info["status"] != "ready_to_combine"
                or upload_info["received_chunks"] != upload_info["total_chunks"]
            ):
                raise ValidationException(
                    message=f"Upload {upload_id} is not ready to complete",
                    details={
                        "uploadId": upload_id,
                        "status": upload_info["status"],
                        "received": upload_info["received_chunks"],
                        "total": upload_info["total_chunks"],
                    },
                )

            # Extract report ID if it's in the chunks directory path
            chunks_dir = upload_info["chunks_dir"]
            report_id = None

            # Try to extract report ID from path
            path_parts = chunks_dir.split(os.path.sep)
            for part in path_parts:
                if len(part) == 36 and "-" in part:  # Simple UUID check
                    try:
                        # Validate it's a proper UUID
                        uuid_obj = uuid.UUID(part)
                        report_id = str(uuid_obj)
                        break
                    except ValueError:
                        continue

            # Determine target directory
            target_dir = os.path.dirname(chunks_dir)

            # Complete the upload using FileProcessor
            result = FileProcessor.complete_chunked_upload(
                upload_id=upload_id, target_directory=target_dir
            )

            # Create a database record for the file
            file_path = result["file_path"]
            file_info = result["file_info"]
            file_id = str(uuid.uuid4())

            file_record = {
                "file_id": file_id,
                "original_filename": result["original_filename"],
                "file_path": file_path,
                "file_size": file_info["size_bytes"],
                "mime_type": result["mime_type"],
                "uploaded_at": datetime.now().isoformat(),
                "processed": False,
            }

            # Store file record in database
            file_response = await supabase.table("files").insert(file_record).execute()

            if not file_response.data:
                raise DatabaseException(
                    message="Failed to create file record",
                    details={"operation": "insert", "table": "files"},
                )

        # Process file in background if it's a document
        if report_id and FileProcessor.is_text_file(file_path):
            background_tasks.add_task(
                process_file_in_background, file_path, file_record, report_id
            )

        # Cleanup chunked upload data (keep metadata for troubleshooting)
        # This could be done by a periodic cleanup task instead

        return {
            "status": "success",
            "data": {
                "fileId": file_id,
                "filename": result["original_filename"],
                "filePath": file_path,
                "fileSize": file_info["size_bytes"],
                "mimeType": result["mime_type"],
                "reportId": report_id,
            },
        }
    except ValueError as e:
        logger.error(f"Error completing chunked upload: {str(e)}")
        raise ValidationException(
            message=str(e), details={"uploadId": request.uploadId}
        )
    except Exception as e:
        logger.error(f"Error completing chunked upload: {str(e)}")
        raise InternalServerException(
            message="Failed to complete chunked upload", details={"error": str(e)}
        )


@router.get("/chunked/status/{upload_id}", response_model=APIResponse[Dict[str, Any]])
@api_error_handler
async def get_chunked_upload_status(upload_id: str):
    """
    Get status of a chunked upload

    Args:
        upload_id: Upload ID from init_chunked_upload

    Returns:
        Standardized API response with upload status
    """
    try:
        # Get upload status using FileProcessor
        upload_info = FileProcessor.get_chunked_upload_status(upload_id)

        if not upload_info:
            raise ValidationException(
                message=f"Upload {upload_id} not found", details={"uploadId": upload_id}
            )

        return {
            "status": "success",
            "data": {
                "uploadId": upload_id,
                "status": upload_info["status"],
                "filename": upload_info["filename"],
                "fileSize": upload_info["file_size"],
                "received": upload_info["received_chunks"],
                "total": upload_info["total_chunks"],
                "progress": (
                    upload_info["received_chunks"] / upload_info["total_chunks"]
                )
                * 100,
                "completed": upload_info["completed"],
            },
        }
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunked upload status: {str(e)}")
        raise InternalServerException(
            message="Failed to get upload status", details={"error": str(e)}
        )


@router.post("/reports", status_code=201)
async def create_empty_report(
    template_id: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Create an empty report for associating files with later

    This is useful when starting with chunked uploads, as we need a report_id
    before uploading any files.

    Authentication:
        This endpoint uses optional authentication. When authenticated, files will be associated
        with the user's account.
    """
    try:
        # Generate a unique report ID (UUID for external reference)
        report_uuid = str(uuid.uuid4())
        logger.info(f"Creating empty report with ID: {report_uuid}")

        # Create a directory for this report
        report_dir = safe_path_join(settings.UPLOAD_DIR, report_uuid)
        os.makedirs(report_dir, exist_ok=True)

        # Store report metadata
        metadata = {
            "report_id": report_uuid,
            "template_id": template_id,
            "files": [],
            "created_at": datetime.now().isoformat(),
            "status": "empty",
            "title": f"Report #{report_uuid[:8]}",
            "content": "",
        }

        metadata_path = safe_path_join(report_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Store in Supabase database
        try:
            supabase = create_supabase_client()

            db_metadata = {
                "template_id": template_id,
                "title": metadata["title"],
                "content": "",
                "is_finalized": False,
                "file_count": 0,
                "report_id": report_uuid,
                "user_id": current_user.id if current_user else None,
            }

            response = supabase.table("reports").insert(db_metadata).execute()
            logger.info(f"Created empty report in Supabase: {report_uuid}")

            if response.data and len(response.data) > 0:
                db_id = response.data[0]["id"]
                mapping_path = safe_path_join(report_dir, "id_mapping.json")
                with open(mapping_path, "w") as f:
                    json.dump({"report_id": report_uuid, "db_id": db_id}, f, indent=2)

        except Exception as e:
            logger.error(f"Error creating report in Supabase: {str(e)}")

        return {
            "report_id": report_uuid,
            "message": "Empty report created successfully",
        }

    except Exception as e:
        logger.error(f"Error creating empty report: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create report: {str(e)}"
        )


@router.post("/query", response_model=APIResponse[UploadQueryResult], status_code=201)
@api_error_handler
async def upload_query(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
):
    """
    Upload a query template for structuring report generation

    Args:
        file: JSON query file
        name: Query name
        description: Optional query description

    Returns:
        Standardized API response with query details
    """
    # Check file type
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are accepted")

    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the {max_size_mb:.1f} MB limit",
        )

    # Read and validate JSON content
    content = await file.read()
    try:
        query_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    # Validate query structure
    if not isinstance(query_data, dict):
        raise HTTPException(status_code=400, detail="Query must be a JSON object")

    with async_supabase_client_context() as supabase:
        # Create query record
        query_id = str(uuid.uuid4())
        query_record = {
            "query_id": query_id,
            "name": name,
            "description": description,
            "content": query_data,
        }

        query_response = await supabase.table("queries").insert(query_record).execute()
        if not query_response.data:
            raise HTTPException(status_code=500, detail="Failed to create query record")

        created_query = query_response.data[0]

        # Return structured response matching the UploadQueryResult model
        return {
            "status": "success",
            "data": {
                "upload_id": created_query["query_id"],
                "filename": file.filename,
                "status": "completed",
                "progress": 100.0,
                "created_at": datetime.now().isoformat(),
            },
        }


@router.post("/upload/template")
async def upload_template_to_supabase(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Upload a template file to Supabase storage."""
    try:
        async with async_supabase_client_context() as supabase:
            # Read file content
            file_content = await file.read()

            # Upload to Supabase using service
            template = await upload_service.upload_template(
                file=file_content,
                filename=file.filename,
                user_id=current_user["id"],
                description=description,
            )

            return {
                "status": "success",
                "message": "Template uploaded successfully",
                "template": template,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/reference-report")
async def upload_reference_report(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Upload a reference report to Supabase storage."""
    try:
        async with async_supabase_client_context() as supabase:
            # Read file content
            file_content = await file.read()

            # Upload to Supabase using service
            reference_report = await upload_service.upload_reference_report(
                file=file_content,
                filename=file.filename,
                template_id=template_id,
                user_id=current_user["id"],
                description=description,
            )

            return {
                "status": "success",
                "message": "Reference report uploaded successfully",
                "reference_report": reference_report,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/report")
async def upload_report(
    file: UploadFile = File(...),
    reference_report_id: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Upload a generated report to Supabase storage."""
    try:
        async with async_supabase_client_context() as supabase:
            # Read file content
            file_content = await file.read()

            # Upload to Supabase using service
            report = await upload_service.upload_report(
                file=file_content,
                filename=file.filename,
                reference_report_id=reference_report_id,
                user_id=current_user["id"],
                description=description,
            )

            return {
                "status": "success",
                "message": "Report uploaded successfully",
                "report": report,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
