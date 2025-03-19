from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
import requests
import os
import json
from config import settings
from typing import Dict, Any, List, Optional
from services.pdf_extractor import extract_text_from_files, extract_text_from_file
from services.ai_service import generate_report_text, extract_template_variables, refine_report_text
from services.docx_formatter import format_report_as_docx
from services.template_processor import template_processor
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
import asyncio

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


@router.post("/generate")
async def generate_report(
    report_id: str = Form(...),
    additional_info: Optional[str] = Form(None),
    template_name: Optional[str] = Form("template.docx")
) -> Dict[str, Any]:
    """
    Generate a report from uploaded documents and additional information.
    
    Args:
        report_id: ID of the report to generate
        additional_info: Optional additional information to include
        template_name: Optional name of the template to use
        
    Returns:
        Dictionary containing report ID and URLs for preview and download
    """
    try:
        # Get document paths from database
        from services.supabase_service import supabase
        result = supabase.table("reports").select("file_paths").eq("report_id", report_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Report not found")
            
        file_paths = result.data[0].get("file_paths", [])
        if not file_paths:
            raise HTTPException(status_code=400, detail="No documents found for report")
            
        # Extract text from documents
        document_texts = []
        for file_path in file_paths:
            full_path = Path(settings.UPLOAD_DIR) / file_path
            if not full_path.exists():
                logger.warning(f"File not found: {full_path}")
                continue
                
            # Use the enhanced PDF extractor
            extracted_text = extract_text_from_file(str(full_path))
            if not extracted_text.startswith("Error:"):
                document_texts.append(extracted_text)
                
        if not document_texts:
            raise HTTPException(status_code=400, detail="No readable documents found")
            
        # Extract template variables from documents
        template_variables_result = await extract_template_variables(
            "\n\n".join(document_texts),
            additional_info or ""
        )
        
        # Get the variables
        template_variables = template_variables_result.get("variables", {})
        
        # Check which variables the template requires
        template_required_vars = template_processor.analyze_template(template_name)
        
        # Ensure all required variables exist
        for var in template_required_vars:
            if var not in template_variables or not template_variables[var]:
                if var == "data_oggi":
                    # Set current date in Italian format
                    from datetime import datetime
                    months_italian = [
                        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
                    ]
                    today = datetime.now()
                    template_variables[var] = f"{today.day} {months_italian[today.month-1]} {today.year}"
                elif var.startswith("totale_"):
                    template_variables[var] = "€ 0,00"
                else:
                    template_variables[var] = "Non fornito" 
        
        # Generate the report using the template processor
        output_path = template_processor.render_template(
            template_name=template_name,
            variables=template_variables
        )
        
        # Extract report ID from the output path
        output_filename = os.path.basename(output_path)
        new_report_id = output_filename.replace("report_", "").replace(".docx", "")
        
        # Generate preview
        preview_task = asyncio.create_task(generate_preview(new_report_id, Path(output_path)))
        
        # Update database with file path
        supabase.table("reports").update({
            "file_path": output_path,
            "formatted_file_path": output_path,  # Use the same path for both fields
            "status": "completed",
            "template_variables": json.dumps(template_variables)  # Store variables for future reference
        }).eq("report_id", report_id).execute()
        
        return {
            "report_id": new_report_id,
            "preview_url": f"/api/preview/{new_report_id}",
            "download_url": f"/api/download/docx/{new_report_id}",
            "status": "success",
            "fields_needing_attention": template_variables_result.get("fields_needing_attention", [])
        }
        
    except Exception as e:
        handle_exception(e, "Report generation")
        raise


async def generate_preview(report_id: str, report_path: Path) -> None:
    """
    Generate a preview of the report.
    
    Args:
        report_id: ID of the report
        report_path: Path to the report file
    """
    try:
        # Get preview path
        preview_path = docx_service.get_preview_path(report_id)
        
        # Convert DOCX to HTML preview
        from services.docx_service import convert_docx_to_html
        await convert_docx_to_html(report_path, preview_path)
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        # Don't raise the exception as this is a background task


@router.post("/reports/{report_id}/refine")
async def refine_report(report_id: str, request: RefineRequest, background_tasks: BackgroundTasks):
    """Refine an existing report based on user instructions."""
    try:
        # Get the original report path
        report_data = supabase.table("reports").select("file_path,template_variables").eq("report_id", report_id).execute()
        
        if not report_data.data:
            raise HTTPException(status_code=404, detail="Report not found")
            
        original_path = report_data.data[0].get("file_path")
        if not original_path:
            raise HTTPException(status_code=400, detail="Report file path not found")
            
        # Get the original template variables if available
        template_variables = {}
        if report_data.data[0].get("template_variables"):
            try:
                template_variables = json.loads(report_data.data[0].get("template_variables"))
            except:
                logger.warning(f"Could not parse template variables for report {report_id}")
        
        # Refine the report text based on instructions
        refined_variables = await refine_template_variables(template_variables, request.instructions)
        
        # Generate new report with refined variables
        output_path = template_processor.render_template(
            template_name="template.docx",  # Assuming we use the default template
            variables=refined_variables
        )
        
        # Extract report ID from the output path
        output_filename = os.path.basename(output_path)
        new_report_id = output_filename.replace("report_", "").replace(".docx", "")
        
        # Generate preview asynchronously
        background_tasks.add_task(preview_service.generate_preview, new_report_id)
        
        # Update database with new report info
        supabase.table("reports").insert({
            "report_id": new_report_id,
            "parent_report_id": report_id,
            "file_path": output_path,
            "formatted_file_path": output_path,
            "status": "completed",
            "template_variables": json.dumps(refined_variables)
        }).execute()
        
        return {
            "status": "success",
            "report_id": new_report_id,
            "preview_url": f"/api/preview/{new_report_id}",
            "download_url": f"/api/download/docx/{new_report_id}"
        }
        
    except Exception as e:
        handle_exception(e, "Report refinement")
        raise


async def refine_template_variables(original_variables: Dict[str, Any], instructions: str) -> Dict[str, Any]:
    """
    Refine template variables based on user instructions.
    
    Args:
        original_variables: Original template variables
        instructions: User instructions for refinement
        
    Returns:
        Dictionary of refined template variables
    """
    try:
        # Build system prompt for AI extraction
        system_prompt = """
        Sei un assistente specializzato nella modifica di report assicurativi.
        Il tuo compito è aggiornare le variabili di un template DOCX in base alle istruzioni dell'utente.
        
        ISTRUZIONI IMPORTANTI:
        1. Analizza attentamente le istruzioni dell'utente e modifica SOLO ciò che viene richiesto.
        2. Assicurati di mantenere tutte le variabili originali che non devono essere modificate.
        3. Rispetta sempre il formato dei valori (date, importi, elenchi puntati, ecc.).
        4. Fornisci il risultato in formato JSON.
        """
        
        # User prompt with the document and additional info
        user_prompt = f"""
        Ecco le variabili attuali del template:
        {json.dumps(original_variables, indent=2, ensure_ascii=False)}
        
        L'utente ha richiesto le seguenti modifiche:
        {instructions}
        
        Aggiorna le variabili in base alle istruzioni e mantieni inalterate tutte le altre.
        Assicurati che il formato sia corretto per ogni tipo di variabile (date, importi, elenchi puntati, ecc.).
        """
        
        # Call OpenRouter API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await call_openrouter_api(messages)
        
        if response and "choices" in response and len(response["choices"]) > 0:
            # Extract the generated response
            ai_response = response["choices"][0]["message"]["content"]
            
            # Parse the JSON from the response
            try:
                # Try to find and extract JSON from the response
                json_match = re.search(r'```(?:json)?(.*?)```', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    # If no code block, try to find JSON directly
                    json_str = ai_response.strip()
                    
                # Remove any markdown or text before or after the JSON
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx]
                
                refined_variables = json.loads(json_str)
                logger.info(f"Successfully refined variables")
                
                # If the response doesn't have the correct structure, ensure it does
                if not isinstance(refined_variables, dict):
                    refined_variables = {"variables": original_variables}
                
                # Check if 'variables' key exists, if not, it's a flat structure
                if "variables" in refined_variables:
                    refined_variables = refined_variables["variables"]
                    
                return refined_variables
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from AI response: {str(e)}")
                logger.error(f"Response was: {ai_response}")
                return original_variables
        
        logger.error("Failed to get usable response from OpenRouter API")
        return original_variables
        
    except Exception as e:
        handle_exception(e, "Template variable refinement")
        return original_variables


# Cleanup task to run periodically
@router.on_event("startup")
@router.on_event("shutdown")
async def cleanup_old_files():
    """Clean up old preview files on startup and shutdown."""
    preview_service.cleanup_old_previews()
