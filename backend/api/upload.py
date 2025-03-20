from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Request, Query, Header, Depends, BackgroundTasks
from typing import List, Dict, Optional, Any
from fastapi.responses import JSONResponse
import os
import uuid
import json
from config import settings
import datetime
from supabase import create_client, Client
import mimetypes
import shutil
from models import Template, File as FileModel, User
from services.pdf_extractor import extract_pdf_metadata, extract_text_from_file
from werkzeug.utils import secure_filename
from utils.supabase_helper import create_supabase_client, supabase_client_context
from pydantic import UUID4
from utils.auth import get_current_user

router = APIRouter()


@router.post("/template", response_model=Template, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form("1.0"),
):
    """
    Upload a reference PDF template for formatting future reports
    """
    # Check file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are accepted"
        )

    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the {max_size_mb:.1f} MB limit",
        )

    try:
        async with supabase_client_context() as supabase:
            # Create template record
            template_data = {
                "template_id": str(uuid.uuid4()),
                "name": name,
                "version": version,
                "content": "",  # Will be updated after file processing
                "meta_data": {}
            }
            
            template_response = await supabase.table("templates").insert(template_data).execute()
            if not template_response.data:
                raise HTTPException(status_code=500, detail="Failed to create template record")
            
            template = template_response.data[0]
            template_id = UUID4(template["template_id"])
            
            # Create unique filename using template_id
            filename = f"template_{template_id}.pdf"
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Extract content from PDF
            content = extract_text_from_file(file_path)
            
            # Update template with file info
            await supabase.table("templates").update({
                "file_path": file_path,
                "content": content
            }).eq("template_id", str(template_id)).execute()
            
            return template
            
    except Exception as e:
        # Clean up file if it was created
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files", status_code=201)
async def upload_files(
    files: List[UploadFile] = File(...),
    report_id: Optional[UUID4] = Form(None)
) -> Dict[str, Any]:
    """
    Upload multiple files and associate them with a report if provided
    """
    try:
        uploaded_files = []
        async with supabase_client_context() as supabase:
            for file in files:
                # Generate file_id
                file_id = uuid.uuid4()
                
                # Create unique filename using file_id
                original_filename = secure_filename(file.filename)
                filename = f"{file_id}_{original_filename}"
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                
                # Save file
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                # Get file info
                file_size = os.path.getsize(file_path)
                mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                
                # Extract content if it's a text-based file
                content = None
                if mime_type in ["text/plain", "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                    content = extract_text_from_file(file_path)
                
                # Create file record
                file_data = {
                    "file_id": str(file_id),
                    "report_id": str(report_id) if report_id else None,
                    "filename": original_filename,
                    "file_path": file_path,
                    "file_type": mime_type,
                    "mime_type": mime_type,
                    "file_size": file_size,
                    "content": content
                }
                
                file_response = await supabase.table("files").insert(file_data).execute()
                if not file_response.data:
                    raise HTTPException(status_code=500, detail=f"Failed to create file record for {original_filename}")
                
                uploaded_files.append(file_response.data[0])
        
        return {
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files
        }
        
    except Exception as e:
        # Clean up any files that were created
        for file_info in uploaded_files:
            if os.path.exists(file_info["file_path"]):
                os.remove(file_info["file_path"])
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents", status_code=201)
async def upload_documents(
    files: List[UploadFile] = File(...),
    template_id: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),  # Add authentication
):
    """
    Upload case-specific documents to generate a report
    
    Authentication:
        This endpoint uses optional authentication. When authenticated, files will be associated
        with the user's account. When not authenticated, files are only accessible via the returned
        report_id.
    """
    try:
        print(f"Upload documents request received: {len(files)} files, template_id={template_id}")
        
        # Check total size of all files
        total_size = sum(file.size for file in files)
        max_total_size = settings.MAX_UPLOAD_SIZE  # 100MB by default
        
        print(f"Total size of all files: {total_size} bytes / {total_size/(1024*1024):.2f} MB")
        print(f"Maximum allowed combined size: {max_total_size} bytes / {max_total_size/(1024*1024):.2f} MB")
        
        if total_size > max_total_size:
            raise HTTPException(
                status_code=400,
                detail=f"Total size of all files ({total_size/(1024*1024):.2f} MB) exceeds the {max_total_size/(1024*1024):.2f} MB combined limit"
            )
        
        uploaded_files = []
        file_processing_log = []
        
        # Generate a unique report ID (UUID for external reference)
        report_uuid = str(uuid.uuid4())
        print(f"Generated report UUID: {report_uuid}")
        
        # Create a directory for this report's files using the UUID
        report_dir = os.path.join(settings.UPLOAD_DIR, report_uuid)
        os.makedirs(report_dir, exist_ok=True)
        print(f"Created report directory: {report_dir}")

        # Initialize Supabase client
        supabase = create_supabase_client()
        supabase_urls = []

        for file in files:
            try:
                print(f"Processing file: {file.filename}, size: {file.size}, content_type: {file.content_type}")
                file_processing_log.append(f"Processing file: {file.filename}, size: {file.size}, content_type: {file.content_type}")
                
                # Check file type
                file_extension = os.path.splitext(file.filename)[1].lower()
                allowed_extensions = [".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png"]
                
                if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                    error_msg = f"Unsupported file type: {file_extension}. Only PDF, Word, text files and images are accepted"
                    file_processing_log.append(f"ERROR: {error_msg}")
                    raise HTTPException(
                        status_code=400,
                        detail=error_msg,
                    )
                
                # Individual file size check is no longer needed since we check total size above
                # But keeping a relaxed limit for individual files (80% of max)
                individual_max = int(max_total_size * 0.8)  # 80% of max allowed size
                if file.size > individual_max:
                    max_size_mb = individual_max / (1024 * 1024)
                    error_msg = f"Individual file size ({file.size/(1024*1024):.2f} MB) exceeds {max_size_mb:.1f} MB limit"
                    file_processing_log.append(f"ERROR: {error_msg}")
                    raise HTTPException(
                        status_code=400,
                        detail=error_msg
                    )

                # Create unique filename
                ext = os.path.splitext(file.filename)[1]
                safe_filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}{ext}"
                file_path = os.path.join(report_dir, filename)
                
                # Save original filename mapping for reference
                original_filename = file.filename

                # Save file locally
                print(f"Saving file to: {file_path}")
                file_processing_log.append(f"Saving file to: {file_path}")
                
                try:
                    file_content = await file.read()  # Read the file content
                    
                    with open(file_path, "wb") as buffer:
                        buffer.write(file_content)  # Write the content to the file
                    
                    # Reset the file cursor for potential future read operations
                    await file.seek(0)
                    
                    # Check if file was saved correctly
                    if os.path.exists(file_path):
                        saved_size = os.path.getsize(file_path)
                        if saved_size == 0:
                            file_processing_log.append(f"WARNING: File was saved but is empty (0 bytes): {file_path}")
                        elif saved_size != file.size:
                            file_processing_log.append(f"WARNING: File size mismatch. Original: {file.size}, Saved: {saved_size}")
                        else:
                            file_processing_log.append(f"Successfully saved file: {file_path} ({saved_size} bytes)")
                    else:
                        file_processing_log.append(f"ERROR: File was not saved successfully: {file_path}")
                        
                except Exception as save_error:
                    error_msg = f"Error saving file {file.filename}: {str(save_error)}"
                    print(error_msg)
                    file_processing_log.append(f"ERROR: {error_msg}")
                    raise Exception(error_msg)
                    
                # Try to upload to Supabase Storage
                try:
                    storage_path = f"reports/{report_uuid}/{filename}"
                    
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                        
                    print(f"Uploading to Supabase: {storage_path}")
                    file_processing_log.append(f"Uploading to Supabase: {storage_path}")
                    
                    # Determine correct content type
                    content_type = file.content_type
                    if not content_type or content_type == "application/octet-stream":
                        # Try to infer content type from extension
                        content_type = mimetypes.guess_type(file_path)[0] or f"application/{ext.replace('.', '')}"
                    
                    response = supabase.storage.from_("reports").upload(
                        path=storage_path,
                        file=file_data,
                        file_options={"content-type": content_type}
                    )
                    
                    # Get public URL
                    public_url = supabase.storage.from_("reports").get_public_url(storage_path)
                    supabase_urls.append(public_url)
                    print(f"Uploaded to Supabase, public URL: {public_url}")
                    file_processing_log.append(f"Successfully uploaded to Supabase: {public_url}")
                    
                except Exception as e:
                    print(f"Error uploading to Supabase (continuing with local file): {str(e)}")
                    file_processing_log.append(f"WARNING: Error uploading to Supabase: {str(e)}")
                    public_url = None
                    storage_path = None
                    
                # Add file information to uploaded_files list
                uploaded_files.append(
                    {
                        "filename": original_filename,
                        "path": file_path,
                        "type": ext.lower().replace(".", ""),
                        "storage_path": storage_path if 'storage_path' in locals() else None,
                        "public_url": public_url
                    }
                )
            except Exception as file_error:
                print(f"Error processing file {file.filename}: {str(file_error)}")
                file_processing_log.append(f"ERROR: Error processing file {file.filename}: {str(file_error)}")
                import traceback
                trace = traceback.format_exc()
                file_processing_log.append(f"Traceback: {trace}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error processing file {file.filename}: {str(file_error)}"
                )
            finally:
                # Ensure the file is closed
                await file.close()

        # Store report metadata in local JSON file
        metadata_path = os.path.join(report_dir, "metadata.json")
        metadata = {
            "report_id": report_uuid,  # Store the UUID for external reference
            "template_id": template_id,
            "files": uploaded_files,
            "created_at": datetime.datetime.now().isoformat(),
            "status": "uploaded",
            "title": f"Report #{report_uuid[:8]}",  # Default title using part of the UUID
            "content": "",  # Initialize empty content
            "processing_log": file_processing_log  # Add processing log for debugging
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved metadata to: {metadata_path}")
        
        # Store metadata in Supabase database
        try:
            print("Saving metadata to Supabase database")
            # Note: We don't include the 'id' field in the database insert
            # The database will generate its own integer ID
            db_metadata = {
                "template_id": template_id,
                "title": metadata["title"],
                "content": "",
                "is_finalized": False,
                "file_count": len(uploaded_files),
                "report_id": report_uuid  # Store the UUID for reference
            }
            response = supabase.table("reports").insert(db_metadata).execute()
            print("Saved report metadata to Supabase:", response)
            
            # Get the database-generated integer ID
            if response.data and len(response.data) > 0:
                db_id = response.data[0]["id"]
                # Save the mapping between UUID and integer ID
                mapping_path = os.path.join(report_dir, "id_mapping.json")
                with open(mapping_path, "w") as f:
                    json.dump({"report_id": report_uuid, "db_id": db_id}, f, indent=2)
                print(f"Created ID mapping: report_id {report_uuid} -> Database ID {db_id}")
                
                # Return the database ID in the response
                return {
                    "message": f"Successfully uploaded {len(uploaded_files)} files",
                    "files": uploaded_files,
                    "report_id": report_uuid,  # Keep returning the UUID for backward compatibility
                    "db_id": db_id,  # Also return the database ID
                    "supabase_urls": supabase_urls if supabase_urls else None,
                    "processing_log": file_processing_log
                }
            
        except Exception as e:
            print(f"Error saving report metadata to Supabase (continuing with local file): {str(e)}")
            file_processing_log.append(f"WARNING: Error saving metadata to Supabase: {str(e)}")
        
        return {
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files,
            "report_id": report_uuid,
            "supabase_urls": supabase_urls if supabase_urls else None,
            "processing_log": file_processing_log
        }
    except Exception as e:
        print(f"Error in upload_documents: {str(e)}")
        import traceback
        trace = traceback.format_exc()
        print(trace)
        # Include the traceback in the error response for better debugging
        raise HTTPException(
            status_code=500, 
            detail=f"Upload failed: {str(e)}\nTraceback: {trace}"
        )


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
        ".pdf", ".doc", ".docx", ".txt", ".rtf", 
        ".jpg", ".jpeg", ".png"
    ]
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if not any(file_ext.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Only PDF, Word, text files and images are accepted"
        )
    
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        max_size_gb = settings.MAX_UPLOAD_SIZE / (1024 * 1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the {max_size_gb:.2f} GB limit"
        )
    
    # Create unique filename
    unique_id = str(uuid.uuid4())
    safe_filename = secure_filename(file.filename)
    new_filename = f"{unique_id}_{safe_filename}"
    
    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, new_filename)
    
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
        if content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raise HTTPException(
                status_code=400,
                detail="File must be a DOCX document"
            )
        
        # Check file size
        if file.size > settings.MAX_UPLOAD_SIZE:
            max_size_gb = settings.MAX_UPLOAD_SIZE / (1024 * 1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds the {max_size_gb:.2f} GB limit"
            )
        
        # Ensure the reference_reports directory exists
        template_dir = os.path.join("backend", "reference_reports")
        os.makedirs(template_dir, exist_ok=True)
        
        # Define the path where the template will be saved
        template_path = os.path.join(template_dir, "template.docx")
        
        # Save the file
        with open(template_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "status": "success",
            "message": "Template uploaded successfully",
            "path": template_path
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
            "size": files.size
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
                print(f"  - Key: {key}, Type: {type(value)}, Class: {value.__class__.__name__}")
                if hasattr(value, "filename"):
                    print(f"     Filename: {value.filename}, Size: {value.size if hasattr(value, 'size') else 'unknown'}")
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
            "form_keys": [key for key in form.keys()] if form else []
        }
        
    except Exception as e:
        print(f"Error in debug endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
