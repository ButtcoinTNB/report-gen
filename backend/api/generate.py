from fastapi import APIRouter, HTTPException, BackgroundTasks
import requests
import os
import json
from config import settings
from typing import Dict, Any, List, Optional
from services.pdf_extractor import extract_text_from_files, extract_text_from_file
from services.ai_service import generate_case_summary, generate_report_text, extract_template_variables, refine_report_text
from services.docx_formatter import format_report_as_docx
from utils.id_mapper import ensure_id_is_int
import time
import re
from fastapi import Depends
from sqlalchemy.orm import Session
from models import Report, File, User
from utils.error_handler import logger, handle_exception
from utils.auth import get_current_user
from utils.db import get_db
from pydantic import BaseModel
import uuid
from api.schemas import GenerateReportRequest, AdditionalInfoRequest
from services.storage import get_document_path
import logging
from services.docx_service import docx_service
from services.preview_service import preview_service
from pathlib import Path

router = APIRouter(tags=["Report Generation"])
logger = logging.getLogger(__name__)


class StructureReportRequest(BaseModel):
    """Request model for generating a report from a specific structure"""
    document_ids: List[int]
    title: Optional[str] = None
    structure: Optional[str] = None


class AnalyzeRequest(BaseModel):
    document_ids: List[str]
    additional_info: str = ""


class GenerateRequest(BaseModel):
    document_ids: List[str]
    additional_info: str = ""


class RefineRequest(BaseModel):
    instructions: str


def fetch_reference_reports():
    """
    Fetches stored reference reports from Supabase or local files.
    
    Returns:
        List of reference report data with extracted text
    """
    try:
        from supabase import create_client, Client
        
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Fetch reference reports from the database
        response = supabase.table("reference_reports").select("*").execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Successfully fetched {len(response.data)} reference reports from Supabase")
            
            # Ensure each report has the expected fields
            valid_reports = []
            for report in response.data:
                if "extracted_text" in report and report["extracted_text"]:
                    valid_reports.append(report)
                else:
                    print(f"Warning: Reference report {report.get('id', 'unknown')} missing extracted text")
                    
            if valid_reports:
                return valid_reports
            else:
                print("No valid reference reports found in Supabase (missing extracted text)")
                # Fall through to local file check
        else:
            print("No reference reports found in Supabase, or empty response")
            # Fall through to local file check
            
    except Exception as e:
        print(f"Error fetching reference reports from Supabase: {str(e)}")
    
    # Search for local files
    reference_data = []
    
    # Check different possible locations for reference reports
    possible_dirs = [
        os.path.join("backend", "reference_reports"),  # Check inside backend folder
        "reference_reports",  # Check in root folder
        os.path.join(settings.UPLOAD_DIR, "templates")  # Check in templates directory
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"Looking for reference reports in {dir_path}")
            
            # Look for PDFs, Word docs, and text files
            reference_files = [
                os.path.join(dir_path, f) 
                for f in os.listdir(dir_path) 
                if f.lower().endswith((".pdf", ".docx", ".doc", ".txt"))
            ]
            
            if reference_files:
                print(f"Found {len(reference_files)} reference files: {[os.path.basename(f) for f in reference_files]}")
                
                for file_path in reference_files:
                    try:
                        print(f"Extracting text from reference file: {file_path}")
                        extracted_text = extract_text_from_file(file_path)
                        
                        if not extracted_text or extracted_text.startswith("Error:"):
                            print(f"Warning: Could not extract text from {file_path}: {extracted_text}")
                            continue
                            
                        reference_data.append({
                            "id": os.path.basename(file_path),
                            "name": os.path.basename(file_path),
                            "extracted_text": extracted_text,
                            "file_path": file_path
                        })
                        print(f"Successfully extracted {len(extracted_text)} characters from {file_path}")
                    except Exception as e:
                        print(f"Error extracting text from {file_path}: {str(e)}")
                
                if reference_data:
                    print(f"Successfully loaded {len(reference_data)} reference documents")
                    return reference_data
                else:
                    print(f"Could not extract text from any files in {dir_path}, trying next directory")
                    
    if not reference_data:
        print("No reference reports found in any local directories")
        
    return reference_data


def get_report_files(report_id: str) -> List[Dict[str, Any]]:
    """
    Get the list of files associated with a report_id from the metadata file.
    
    Args:
        report_id: The ID of the report to get files for
        
    Returns:
        List of file information dictionaries
    """
    report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
    metadata_path = os.path.join(report_dir, "metadata.json")
    
    if not os.path.exists(metadata_path):
        return []
    
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            return metadata.get("files", [])
    except Exception as e:
        print(f"Error reading report metadata: {str(e)}")
        return []


@router.post("/")
async def generate_report(text: dict):
    reference_reports = fetch_reference_reports()

    if not reference_reports:
        return {"error": "No reference reports found in database or local directories."}

    # Use all available reference reports, but limit total context size 
    # to avoid exceeding token limits
    max_report_chars = 20000  # Adjust based on token limits of your model
    context = ""
    reports_used = 0
    
    # Sort by relevance, assuming shorter reports are more likely to be relevant templates
    # This is a simple heuristic - you might want to implement more sophisticated selection
    sorted_reports = sorted(
        reference_reports, 
        key=lambda r: len(r.get("extracted_text", "")),
    )
    
    # Extract format and structure WITHOUT content
    report_sections = []
    section_formats = {}
    
    for report in sorted_reports[:2]:  # Limit to 2 reference reports
        report_text = report.get("extracted_text", "")
        if not report_text.strip():
            continue
            
        # Extract just the section headers and layout structure
        sections = re.findall(r'^([A-Z][A-Z\s]+)(?::|\n)', report_text, re.MULTILINE)
        if sections:
            report_sections.extend(sections)
    
    # Remove duplicates and create a structured format template
    report_sections = list(dict.fromkeys(report_sections))
    
    # Create a format template with placeholders instead of actual content
    format_template = ""
    for section in report_sections:
        format_template += f"## {section}\n[Format placeholder for {section}]\n\n"
    
    if not format_template:
        format_template = """
## RIEPILOGO SINISTRO
[Format placeholder for claim summary]

## INFORMAZIONI SUL RICHIEDENTE
[Format placeholder for claimant information]

## DETTAGLI INCIDENTE
[Format placeholder for incident details]

## ANALISI COPERTURA
[Format placeholder for coverage analysis]

## DANNI/FERITE
[Format placeholder for damages/injuries]

## RISULTATI INVESTIGAZIONE
[Format placeholder for investigation findings]

## VALUTAZIONE RESPONSABILITÀ
[Format placeholder for liability assessment]

## RACCOMANDAZIONE RISARCIMENTO 
[Format placeholder for settlement recommendation]
"""
    
    print(f"Created format template with {len(report_sections)} sections")

    # Updated with stricter instructions and format-only reference
    prompt = (
        "Sei un esperto redattore di relazioni assicurative incaricato di creare una relazione formale assicurativa.\n\n"
        "ISTRUZIONI RIGOROSE - SEGUI CON PRECISIONE:\n"
        "1. SOLO FORMATO: Utilizza il modello di formato solo per strutturare la tua relazione in modo professionale.\n"
        "2. SOLO CONTENUTO UTENTE: Il contenuto della tua relazione DEVE provenire ESCLUSIVAMENTE dalle note del caso dell'utente.\n"
        "3. NESSUNA INVENZIONE: Non aggiungere ALCUNA informazione non esplicitamente presente nelle note del caso.\n"
        "4. LINGUA ITALIANA: Scrivi la relazione SEMPRE in italiano, indipendentemente dalla lingua delle note del caso.\n"
        "5. INFORMAZIONI MANCANTI: Se mancano informazioni chiave, indica 'Non fornito nei documenti' anziché inventarle.\n"
        "6. NESSUNA CREATIVITÀ: Questo è un documento assicurativo fattuale - attieniti strettamente alle informazioni nelle note del caso.\n\n"
        f"MODELLO DI FORMATO (usa SOLO per la struttura):\n{format_template}\n\n"
        f"NOTE DEL CASO (UNICA FONTE PER IL CONTENUTO):\n{text['content']}\n\n"
        "Genera una relazione strutturata di sinistro assicurativo che segue il formato del modello ma "
        "utilizza SOLO fatti dalle note del caso. Includi sezioni appropriate come:\n"
        "- RIEPILOGO SINISTRO\n"
        "- INFORMAZIONI SUL RICHIEDENTE\n"
        "- DETTAGLI INCIDENTE\n"
        "- ANALISI COPERTURA\n"
        "- DANNI/FERITE\n"
        "- RISULTATI INVESTIGAZIONE\n"
        "- VALUTAZIONE RESPONSABILITÀ\n"
        "- RACCOMANDAZIONE RISARCIMENTO\n\n"
        "FONDAMENTALE: NON inventare ALCUNA informazione. Utilizza solo fatti esplicitamente dichiarati nelle note del caso."
    )

    # Updated to use messages array with system message like /from-id endpoint
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": settings.DEFAULT_MODEL,
            "messages": [
                {
                    "role": "system", 
                    "content": "Sei un esperto redattore di relazioni assicurative. DEVI utilizzare SOLO fatti esplicitamente dichiarati nelle note del caso dell'utente. Non inventare, presumere o allucinare ALCUNA informazione non esplicitamente fornita. Rimani strettamente fattuale. NON utilizzare ALCUNA informazione dal modello di formato per il contenuto - serve SOLO per la struttura. Scrivi SEMPRE in italiano, indipendentemente dalla lingua di input."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2  # Lower temperature for more factual output
        },
        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
    )

    return response.json()


@router.post("/from-id")
async def generate_report_from_id(data: Dict[str, Any]):
    """Generate a report from uploaded document IDs"""
    try:
        document_ids = data.get("document_ids", [])
        if not document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")
            
        # Get the report directory
        report_id = str(uuid.uuid4())
        report_dir = get_report_directory(report_id)
        
        # Get document paths
        document_paths = []
        for doc_id in document_ids:
            # Convert string IDs to integers if needed
            doc_id = ensure_id_is_int(doc_id)
            if not doc_id:
                continue
                
            # Get document info
            doc_info = get_report_files(str(doc_id))
            if not doc_info:
                continue
                
            # Add document paths
            for file_info in doc_info:
                file_path = file_info.get("path")
                if file_path and os.path.exists(file_path):
                    document_paths.append(file_path)
        
        if not document_paths:
            raise HTTPException(
                status_code=400,
                detail="No valid documents found for the provided IDs"
            )
            
        # Generate the report content
        result = await generate_report_text(document_paths)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        # Format the report as DOCX using template variables
        docx_result = await format_report_as_docx(
            report_content=result["report_text"],
            template_variables=result["template_variables"],
            filename=f"report_{report_id}.docx"
        )
        
        return {
            "report_id": report_id,
            "docx_path": docx_result["docx_path"],
            "filename": docx_result["filename"]
        }
            
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Very simple test endpoint to check routing
@router.post("/simple-test")
async def simple_test(data: Dict[str, Any]):
    """A very simple test endpoint to check routing"""
    return {"message": "Simple test endpoint works!", "received": data}


@router.post("/summarize")
async def summarize_documents(data: Dict[str, Any]):
    """
    Generate a brief summary of uploaded documents
    
    Args:
        data: A dictionary containing report_id
        
    Returns:
        Brief summary and key facts
    """
    report_id = data.get("report_id")
    
    if not report_id:
        raise HTTPException(status_code=400, detail="report_id is required")
    
    print(f"Received summary request for ID: {report_id}")
    
    try:
        # If report_id is a UUID, the files will be in a directory named with the UUID
        report_files = get_report_files(report_id)
        
        if not report_files:
            raise HTTPException(
                status_code=404, 
                detail=f"No files found for report ID: {report_id}"
            )
        
        # Log file information for debugging
        print(f"Found {len(report_files)} files for report ID {report_id}:")
        for idx, file in enumerate(report_files):
            print(f"  File {idx+1}: {file['filename']} ({file['type']}) at {file['path']}")
            
            # Check if files actually exist
            if not os.path.exists(file['path']):
                print(f"WARNING: File path doesn't exist: {file['path']}")
        
        # Extract file paths
        file_paths = [file["path"] for file in report_files]
        
        # Extract text from files first to validate content
        try:
            extraction_start_time = time.time()
            print(f"Starting text extraction from {len(file_paths)} files for summary...")
            
            extracted_text = extract_text_from_files(file_paths)
            extraction_time = time.time() - extraction_start_time
            print(f"Text extraction completed in {extraction_time:.2f} seconds")
            
            # Check for OCR markers or errors
            ocr_markers = ["[OCR failed", "No readable text detected in image", "Image file detected"]
            has_ocr_content = any(marker in extracted_text for marker in ocr_markers)
            has_error = extracted_text.startswith("Error:") or "Error extracting text" in extracted_text
            
            # Check if we have an extraction error
            if has_error:
                error_msg = "Error extracting text from documents"
                print(f"WARNING: {error_msg} - {extracted_text}")
                return {
                    "summary": f"We encountered an issue processing your documents. {extracted_text.split('.')[0]}.",
                    "key_facts": [],
                    "error": extracted_text
                }
                
            # Check for minimal content from OCR
            if has_ocr_content and len(extracted_text.strip()) < 300:
                print("WARNING: Document appears to be primarily image-based with little text")
                return {
                    "summary": "Your document appears to be primarily image-based. While we've attempted to extract text using OCR technology, the results are too limited for a proper summary. For best results, please consider uploading a text-based document.",
                    "key_facts": [
                        "Document is primarily image-based",
                        "Limited text content could be extracted",
                        "OCR results may be unreliable",
                        "Consider providing a text-based document"
                    ],
                    "ocr_limited": True
                }
                
            # If very little content overall, return a helpful message
            if len(extracted_text.strip()) < 100:
                print("WARNING: Extracted less than 100 characters of text")
                return {
                    "summary": "We could only extract a very small amount of text from your documents. This may be because the documents are image-based, password-protected, or in a format we can't fully process.",
                    "key_facts": [
                        "Limited text content extracted",
                        "Document may be primarily graphical",
                        "Consider providing a text-based version"
                    ],
                    "limited_content": True
                }
            
        except Exception as extract_error:
            error_msg = f"Error during text extraction: {str(extract_error)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            return {
                "summary": "Error processing documents. Please try uploading in a different format.",
                "key_facts": [],
                "error": str(extract_error)
            }
            
        # Generate the summary using our AI function that includes strict factual instructions
        try:
            # Pass additional context if we have OCR content
            ocr_context = ""
            if has_ocr_content:
                ocr_context = "Note: Some content appears to be from OCR of images and may contain errors. Focus on the most reliable information."
                
            summary_result = await generate_case_summary(file_paths, ocr_context)
            
            print(f"Generated summary: {summary_result['summary']}")
            print(f"Key facts identified: {len(summary_result['key_facts'])}")
            
            # Add a note to the summary if OCR was used
            if has_ocr_content:
                summary_result["summary"] = "Note: Your document appears to contain image-based content. Our system used OCR to extract text, which may result in some inaccuracies. " + summary_result["summary"]
                summary_result["ocr_used"] = True
                
            return summary_result
            
        except Exception as summary_error:
            error_msg = f"Error generating summary: {str(summary_error)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            return {
                "summary": f"Error generating summary: {str(summary_error)}. Please try again.",
                "key_facts": [],
                "error": str(summary_error)
            }
        
    except Exception as e:
        print(f"Error in summarize_documents endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "summary": f"Error processing request: {str(e)}. Please try again.",
            "key_facts": [],
            "error": str(e)
        }


@router.post("/from-structure")
async def generate_from_structure(
    request: StructureReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a report from uploaded documents using a specific structure."""
    logger.info(f"Generating report from structure for user {current_user.id}")
    
    try:
        # Create a report record
        report = Report(
            title=request.title or "Generated Report",
            user_id=current_user.id,
            status="processing"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id
        
        logger.info(f"Created report record with ID: {report_id}")
        
        # Create temp directory for this report
        report_dir = get_report_directory(report_id)
        os.makedirs(report_dir, exist_ok=True)
        
        # Prepare file paths for documents
        document_paths = []
        
        # Handle file IDs - convert them to file paths
        for file_id in request.document_ids:
            # Get file path from database
            file_record = db.query(File).filter(File.id == file_id).first()
            if not file_record:
                logger.warning(f"File with ID {file_id} not found")
                continue
                
            # Verify file existence
            file_path = os.path.join(settings.UPLOAD_DIR, file_record.file_path)
            if not os.path.exists(file_path):
                logger.warning(f"File not found at path: {file_path}")
                continue
                
            document_paths.append(file_path)
            logger.info(f"Added document: {file_path}")
        
        if not document_paths:
            logger.error("No valid documents found for processing")
            db.query(Report).filter(Report.id == report_id).update({"status": "failed"})
            db.commit()
            return {"status": "failed", "error": "No valid documents found for processing"}
        
        # Extract text from documents
        logger.info("Extracting text from documents...")
        from services.pdf_extractor import extract_text_from_files
        document_text = extract_text_from_files(document_paths)
        
        # Get the structure to use
        custom_format_template = request.structure or ""
        
        if not custom_format_template.strip():
            # Create a default format template with placeholders if none provided
            custom_format_template = """
## RIEPILOGO SINISTRO
[Format placeholder for claim summary]

## INFORMAZIONI SUL RICHIEDENTE
[Format placeholder for claimant information]

## DETTAGLI INCIDENTE
[Format placeholder for incident details]

## ANALISI COPERTURA
[Format placeholder for coverage analysis]

## DANNI/FERITE
[Format placeholder for damages/injuries]

## RISULTATI INVESTIGAZIONE
[Format placeholder for investigation findings]

## VALUTAZIONE RESPONSABILITÀ
[Format placeholder for liability assessment]

## RACCOMANDAZIONE RISARCIMENTO
[Format placeholder for settlement recommendation]
"""
        
        # Prepare the system message
        system_message = (
            "Sei un esperto redattore di relazioni assicurative. DEVI utilizzare SOLO fatti esplicitamente dichiarati nei documenti dell'utente. "
            "Non inventare, presumere o allucinare ALCUNA informazione non esplicitamente fornita. Rimani strettamente fattuale. "
            "NON utilizzare ALCUNA informazione dal modello di formato per il contenuto - serve SOLO per la struttura. "
            "Scrivi SEMPRE in italiano, indipendentemente dalla lingua di input."
        )
        
        # Prepare the prompt with strict instructions
        prompt = (
            "Sei un esperto redattore di relazioni assicurative incaricato di creare una relazione formale assicurativa.\n\n"
            "ISTRUZIONI RIGOROSE - SEGUI CON PRECISIONE:\n"
            "1. SOLO FORMATO: Utilizza la struttura del formato per organizzare la tua relazione in modo professionale.\n"
            "2. SOLO CONTENUTO UTENTE: Il contenuto della tua relazione DEVE provenire ESCLUSIVAMENTE dai documenti dell'utente.\n"
            "3. NESSUNA INVENZIONE: Non aggiungere ALCUNA informazione non esplicitamente presente nei documenti dell'utente.\n"
            "4. LINGUA ITALIANA: Scrivi la relazione SEMPRE in italiano, indipendentemente dalla lingua dei documenti dell'utente.\n"
            "5. INFORMAZIONI MANCANTI: Se mancano informazioni chiave, indica 'Non fornito nei documenti' anziché inventarle.\n"
            "6. NESSUNA CREATIVITÀ: Questo è un documento assicurativo fattuale - attieniti strettamente alle informazioni nei documenti dell'utente.\n"
            f"STRUTTURA DEL FORMATO (usa SOLO per l'organizzazione):\n{custom_format_template}\n\n"
            f"DOCUMENTI DELL'UTENTE (UNICA FONTE PER IL CONTENUTO):\n{document_text}\n\n"
            "Genera una relazione strutturata di sinistro assicurativo che segue il formato del modello ma "
            "utilizza SOLO fatti dai documenti dell'utente. Includi sezioni appropriate in base alle informazioni disponibili.\n\n"
            "FONDAMENTALE: NON inventare ALCUNA informazione. Utilizza solo fatti esplicitamente dichiarati nei documenti dell'utente."
        )
        
        # Background task to generate report
        background_tasks.add_task(
            _generate_and_save_report,
            system_message=system_message,
            prompt=prompt,
            report_id=report_id,
            report_dir=report_dir,
            document_text=document_text,
            token_limit=settings.MAX_TOKENS
        )
        
        return {"status": "processing", "report_id": report_id}
        
    except Exception as e:
        logger.error(f"Error in generate_from_structure: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update report status if report was created
        if 'report_id' in locals():
            db.query(Report).filter(Report.id == report_id).update({"status": "failed"})
            db.commit()
            
        # Return error response
        return {"status": "failed", "error": str(e)}


def get_report_directory(report_id):
    """Get the directory path for a report"""
    return os.path.join(settings.UPLOAD_DIR, "reports", str(report_id))


async def _generate_and_save_report(
    system_message: str,
    prompt: str,
    report_id: int,
    report_dir: str,
    document_text: str,
    token_limit: int = 4000
):
    """Generate a report and save it to disk"""
    try:
        logger.info(f"Starting report generation for report ID: {report_id}")
        start_time = time.time()
        
        # Prepare API request
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Log the API call
        logger.info(f"Calling OpenRouter API with prompt length: {len(prompt)} characters")
        
        # Call the OpenRouter API
        response = await call_openrouter_api(
            messages=messages,
            max_retries=2,
            timeout=120.0
        )
        
        # Calculate time taken
        time_taken = time.time() - start_time
        logger.info(f"API call completed in {time_taken:.2f} seconds")
        
        # Process the response
        if (
            response
            and "choices" in response
            and len(response["choices"]) > 0
            and "message" in response["choices"][0]
            and "content" in response["choices"][0]["message"]
        ):
            # Extract the generated text
            generated_text = response["choices"][0]["message"]["content"]
            logger.info(f"Successfully generated report with {len(generated_text)} characters")
            
            # Save the generated text to a file
            output_file = os.path.join(report_dir, "report.md")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(generated_text)
                
            # Update the report record in the database
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            try:
                # Update the report record
                db.query(Report).filter(Report.id == report_id).update({
                    "content": generated_text,
                    "file_path": os.path.join("reports", str(report_id), "report.md"),
                    "status": "completed"
                })
                db.commit()
                logger.info(f"Updated report record for ID: {report_id}")
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                
        else:
            logger.error(f"Unexpected API response format: {response}")
            
            # Update report status to failed
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            try:
                db.query(Report).filter(Report.id == report_id).update({"status": "failed"})
                db.commit()
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                
    except Exception as e:
        logger.error(f"Error in _generate_and_save_report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update report status to failed
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            db.query(Report).filter(Report.id == report_id).update({"status": "failed"})
            db.commit()
        except Exception as db_error:
            logger.error(f"Database error when updating status: {str(db_error)}")


@router.post("/analyze")
async def analyze_documents(request: AnalyzeRequest):
    """Analyze uploaded documents and extract variables."""
    try:
        # Get document paths
        document_paths = [get_document_path(doc_id) for doc_id in request.document_ids]
        
        # Extract variables from documents
        result = await extract_template_variables(
            "\n".join([str(path) for path in document_paths]),
            request.additional_info
        )
        
        return {
            "status": "success",
            "extracted_variables": result["variables"],
            "fields_needing_attention": result.get("fields_needing_attention", [])
        }
        
    except Exception as e:
        handle_exception(e, "Document analysis")
        raise


@router.post("/generate")
async def generate_report(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Generate a DOCX report and return preview/download URLs."""
    try:
        # Get document paths
        document_paths = [get_document_path(doc_id) for doc_id in request.document_ids]
        
        # Generate report content
        result = await generate_report_text(document_paths, request.additional_info)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Generate DOCX report
        report_id = docx_service.generate_report(
            template_variables={
                **result["template_variables"],
                "content": result["report_text"]
            }
        )
        
        # Generate preview asynchronously
        background_tasks.add_task(preview_service.generate_preview, report_id)
        
        # Get URLs for preview and download
        urls = get_file_urls(report_id)
        
        return {
            "status": "success",
            "report_id": report_id,
            "preview_url": urls["preview_url"],
            "download_url": urls["download_url"],
            "fields_needing_attention": result.get("fields_needing_attention", [])
        }
        
    except Exception as e:
        handle_exception(e, "Report generation")
        raise


@router.post("/reports/{report_id}/refine")
async def refine_report(report_id: str, request: RefineRequest, background_tasks: BackgroundTasks):
    """Refine an existing report based on user instructions."""
    try:
        # Get the original report path
        original_path = docx_service.get_report_path(report_id)
        
        # Refine the report text based on instructions
        refined_text = await refine_report_text(str(original_path), request.instructions)
        
        # Generate new report with refined text
        new_report_id = docx_service.modify_report(report_id, {
            "content": refined_text
        })
        
        # Generate preview asynchronously
        background_tasks.add_task(preview_service.generate_preview, new_report_id)
        
        # Get URLs for preview and download
        urls = get_file_urls(new_report_id)
        
        return {
            "status": "success",
            "report_id": new_report_id,
            "preview_url": urls["preview_url"],
            "download_url": urls["download_url"]
        }
        
    except Exception as e:
        handle_exception(e, "Report refinement")
        raise


def get_file_urls(report_id: str) -> dict:
    """Generate preview and download URLs for a report."""
    base_url = "http://localhost:8000/files"  # Update for production
    return {
        "preview_url": f"{base_url}/previews/{report_id}.html",
        "download_url": f"{base_url}/reports/{report_id}.docx"
    }


# Cleanup task to run periodically
@router.on_event("startup")
@router.on_event("shutdown")
async def cleanup_old_files():
    """Clean up old preview files on startup and shutdown."""
    preview_service.cleanup_old_previews()
