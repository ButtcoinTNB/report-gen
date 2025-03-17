from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Request
from typing import List, Dict, Optional
from fastapi.responses import JSONResponse
import os
import uuid
import json
from config import settings
import datetime
from supabase import create_client, Client
import mimetypes
import shutil
from models import Template
from services.pdf_extractor import extract_pdf_metadata, extract_text_from_file
from werkzeug.utils import secure_filename

router = APIRouter()


@router.post("/template", response_model=Template, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
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
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the {settings.MAX_UPLOAD_SIZE} bytes limit",
        )

    # Create unique filename
    filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Save file temporarily
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving file: {str(e)}"
        )
    finally:
        file.file.close()

    # Extract metadata from the PDF
    try:
        metadata = extract_pdf_metadata(file_path)
    except Exception as e:
        # Remove file if metadata extraction fails
        os.remove(file_path)
        raise HTTPException(
            status_code=500, detail=f"Error extracting metadata: {str(e)}"
        )

    # Extract text from the PDF for reference
    extracted_text = extract_text_from_file(file_path)

    # Store template in Supabase Storage
    try:
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Upload file to Supabase Storage
        with open(file_path, "rb") as f:
            file_data = f.read()
            
        storage_path = f"templates/{filename}"
        response = supabase.storage.from_("reports").upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "application/pdf"}
        )
        
        # Get the public URL
        public_url = supabase.storage.from_("reports").get_public_url(storage_path)
        
        # Save template metadata to database
        template_data = {
            "name": name,
            "file_path": storage_path,
            "public_url": public_url,
            "metadata": metadata,
            "extracted_text": extracted_text,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        response = supabase.table("reference_reports").insert(template_data).execute()
        
        # Get the newly created template with ID
        template = response.data[0] if response.data else template_data
        
        # Clean up local file now that it's in Supabase
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return template
        
    except Exception as e:
        # Keep the local file as backup if upload fails
        error_message = f"Error uploading to Supabase: {str(e)}"
        print(error_message)
        
        # If we still have the file locally, we can create a database entry
        # referencing the local file as a fallback
        if os.path.exists(file_path):
            try:
                # Initialize Supabase client
                supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                
                # Create record in database with local file path
                template_data = {
                    "name": name,
                    "file_path": file_path,  # Using local path instead of Supabase URL
                    "meta_data": metadata,
                    "created_at": datetime.datetime.now().isoformat()
                }
                
                response = supabase.table("templates").insert(template_data).execute()
                
                if response.data and len(response.data) > 0:
                    return response.data[0]
            except Exception as db_error:
                print(f"Error creating fallback database record: {str(db_error)}")
        
        # If all else fails, raise a proper exception
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload template to storage: {error_message}"
        )


@router.post("/documents", status_code=201)
async def upload_documents(
    files: List[UploadFile] = File(...),
    template_id: int = Form(1),  # Default value of 1, making it optional
):
    """
    Upload case-specific documents to generate a report
    """
    try:
        print(f"Upload documents request received: {len(files)} files, template_id={template_id}")
        
        uploaded_files = []
        
        # Generate a unique report ID
        report_id = str(uuid.uuid4())
        print(f"Generated report ID: {report_id}")
        
        # Create a directory for this report's files
        report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
        os.makedirs(report_dir, exist_ok=True)
        print(f"Created report directory: {report_dir}")

        # Initialize Supabase client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        supabase_urls = []

        for file in files:
            try:
                print(f"Processing file: {file.filename}, size: {file.size}, content_type: {file.content_type}")
                
                # Check file type
                if not file.filename.lower().endswith(
                    (".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png")
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Only PDF, Word, text files and images are accepted",
                    )

                # Check file size
                if file.size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File size exceeds the {settings.MAX_UPLOAD_SIZE} bytes limit",
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
                file_content = await file.read()  # Read the file content
                
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)  # Write the content to the file
                
                # Reset the file cursor for potential future read operations
                await file.seek(0)
                    
                # Try to upload to Supabase Storage
                try:
                    storage_path = f"reports/{report_id}/{filename}"
                    
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                        
                    print(f"Uploading to Supabase: {storage_path}")
                    response = supabase.storage.from_("reports").upload(
                        path=storage_path,
                        file=file_data,
                        file_options={"content-type": f"application/{ext.replace('.', '')}" if ext != '.png' else "image/png"}
                    )
                    
                    # Get public URL
                    public_url = supabase.storage.from_("reports").get_public_url(storage_path)
                    supabase_urls.append(public_url)
                    print(f"Uploaded to Supabase, public URL: {public_url}")
                    
                except Exception as e:
                    print(f"Error uploading to Supabase (continuing with local file): {str(e)}")
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
            "report_id": report_id,
            "template_id": template_id,
            "files": uploaded_files,
            "created_at": datetime.datetime.now().isoformat(),
            "status": "uploaded"
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved metadata to: {metadata_path}")
        
        # Store metadata in Supabase database
        try:
            print("Saving metadata to Supabase database")
            response = supabase.table("reports").insert(metadata).execute()
            print("Saved report metadata to Supabase:", response)
        except Exception as e:
            print(f"Error saving report metadata to Supabase (continuing with local file): {str(e)}")
        
        return {
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files,
            "report_id": report_id,
            "supabase_urls": supabase_urls if supabase_urls else None
        }
    except Exception as e:
        print(f"Error in upload_documents: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/document", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    report_id: int = Form(None),
    doc_type: str = Form("general"),
):
    """
    Upload a document for report generation.
    
    Args:
        file: The document file to upload
        report_id: Optional report ID to associate with
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
            detail="Only document and image files are allowed"
        )
    
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {max_size_mb:.1f} MB size limit"
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


@router.post("/template", status_code=201)
async def upload_template_docx(file: UploadFile = File(...)):
    """
    Upload a DOCX template file that will be used for generating reports.
    
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
