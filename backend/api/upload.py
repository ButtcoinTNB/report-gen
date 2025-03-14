from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
import os
import uuid
import shutil
from config import settings
from models import Template
from services.pdf_extractor import extract_pdf_metadata, extract_text_from_file
from werkzeug.utils import secure_filename
import json
import datetime
from supabase import create_client, Client

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
    uploaded_files = []
    
    # Generate a unique report ID
    report_id = str(uuid.uuid4())
    
    # Create a directory for this report's files
    report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
    os.makedirs(report_dir, exist_ok=True)

    # Initialize Supabase client
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    supabase_urls = []

    for file in files:
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
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Try to upload to Supabase Storage
            try:
                storage_path = f"reports/{report_id}/{filename}"
                
                with open(file_path, "rb") as f:
                    file_data = f.read()
                    
                response = supabase.storage.from_("reports").upload(
                    path=storage_path,
                    file=file_data,
                    file_options={"content-type": f"application/{ext.replace('.', '')}" if ext != '.png' else "image/png"}
                )
                
                # Get public URL
                public_url = supabase.storage.from_("reports").get_public_url(storage_path)
                supabase_urls.append(public_url)
                
            except Exception as e:
                print(f"Error uploading to Supabase (continuing with local file): {str(e)}")
                public_url = None
                
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
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error saving file: {str(e)}"
            )
        finally:
            file.file.close()

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
    
    # Store metadata in Supabase database
    try:
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
