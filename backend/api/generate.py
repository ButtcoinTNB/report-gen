from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Body, Depends
import requests
import os
import json
from config import settings
from typing import Dict, Any, List, Optional
from services.pdf_extractor import extract_text_from_files, extract_text_from_file
from services.ai_service import (
    generate_report_text, 
    extract_template_variables, 
    refine_report_text, 
    AIServiceError, 
    AIConnectionError, 
    AITimeoutError, 
    AIResponseError, 
    AIParsingError
)
from services.docx_formatter import format_report_as_docx
from services.template_processor import template_processor
import time
import re
from sqlalchemy.orm import Session
from models import Report, File as FileModel, User, Template
from utils.error_handler import logger, handle_exception, api_error_handler, retry_operation
from utils.auth import get_current_user
from utils.db import get_db
from pydantic import BaseModel, UUID4
import uuid
from api.schemas import GenerateReportRequest, AdditionalInfoRequest, APIResponse
from services.storage import get_document_path
import logging
from services.docx_service import docx_service
from services.preview_service import preview_service
from pathlib import Path
import asyncio
from utils.supabase_helper import create_supabase_client, supabase_client_context
from uuid import UUID
from utils.file_utils import safe_path_join
import shutil

router = APIRouter(tags=["Report Generation"])
logger = logging.getLogger(__name__)


class StructureReportRequest(BaseModel):
    """Request model for generating a report from a specific structure"""
    document_ids: List[UUID4]
    title: Optional[str] = None
    structure: Optional[str] = None
    template_id: Optional[UUID4] = None


class AnalyzeRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: str = ""
    report_id: Optional[UUID4] = None  # Make report_id optional to maintain backwards compatibility


class GenerateRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: str = ""
    template_id: Optional[UUID4] = None


class RefineRequest(BaseModel):
    instructions: str


class AnalysisResponseSchema(BaseModel):
    """Schema for analysis response data"""
    findings: Dict[str, Any]
    suggestions: List[str]
    extracted_variables: Dict[str, Any]


class RefineReportResponse(BaseModel):
    """Response model for report refinement endpoint"""
    report_id: str
    content: str
    status: str


class SimpleTestResponse(BaseModel):
    """Response model for simple test endpoint"""
    message: str
    received: Dict[str, Any]


class GenerateDocxResponse(BaseModel):
    """Response model for DOCX report generation endpoint"""
    status: str
    report_id: str


class GenerateFromIdResponse(BaseModel):
    """Response model for generating report from ID endpoint"""
    report_id: str
    content: str
    status: str


class GenerateContentResponse(BaseModel):
    """Response model for report content generation endpoint"""
    report_id: str
    content: str
    status: str


class GenerateReportResponse(BaseModel):
    """Response model for report creation endpoint"""
    report_id: str


def fetch_reference_reports():
    """
    Fetches stored reference reports from Supabase or local files.
    
    Returns:
        List of reference report data with extracted text
    """
    try:
        # Initialize Supabase client using our helper
        supabase = create_supabase_client()
        
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
        safe_path_join("backend", "reference_reports"),  # Check inside backend folder
        "reference_reports",  # Check in root folder
        safe_path_join(settings.UPLOAD_DIR, "templates")  # Check in templates directory
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"Looking for reference reports in {dir_path}")
            
            # Look for PDFs, Word docs, and text files
            reference_files = [
                safe_path_join(dir_path, f) 
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


async def get_report_files(report_id: UUID4) -> List[Dict[str, Any]]:
    """
    Get all files associated with a report.
    
    Args:
        report_id: UUID of the report
        
    Returns:
        List of file information dictionaries
    """
    try:
        supabase = create_supabase_client()
        response = await supabase.table("files").select("*").eq("report_id", str(report_id)).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting report files: {str(e)}")
        return []


@router.post("/", response_model=APIResponse[GenerateReportResponse])
@api_error_handler
async def generate_report(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a new report
    
    Args:
        request: GenerateRequest with document IDs and additional info
        background_tasks: FastAPI background tasks
        
    Returns:
        Standardized API response with the generated report ID
    """
    async with supabase_client_context() as supabase:
        # Create new report
        report_data = {
            "report_id": str(uuid.uuid4()),
            "title": "New Report",
            "status": "draft",
            "template_id": str(request.template_id) if request.template_id else None,
            "metadata": {}
        }
        
        report_response = await supabase.table("reports").insert(report_data).execute()
        if not report_response.data:
            raise HTTPException(status_code=500, detail="Failed to create report")
        
        report = report_response.data[0]
        report_id = UUID(report["report_id"])
        
        # Associate files with report
        for doc_id in request.document_ids:
            await supabase.table("files").update({
                "report_id": str(report_id)
            }).eq("file_id", str(doc_id)).execute()
        
        return {"report_id": str(report_id)}


@router.post("/generate", response_model=APIResponse[GenerateContentResponse])
@api_error_handler
async def generate_report_content(
    request: GenerateRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Generate content for an existing report
    
    Args:
        request: GenerateRequest with document IDs and additional info
        current_user: Optional authenticated user
        
    Returns:
        Standardized API response with generated report content
    
    Authentication:
        This endpoint uses optional authentication. When authenticated, the generated report
        will be associated with the user's account for better tracking and management.
    """
    # Extract values from request
    report_id = request.document_ids[0] if request.document_ids else None
    
    # Use provided report_id if available, otherwise use first document_id
    if hasattr(request, 'report_id') and request.report_id:
        report_id = request.report_id
        
    if not report_id:
        raise HTTPException(
            status_code=400,
            detail="Report ID is required"
        )
        
    additional_info = request.additional_info
    template_id = request.template_id
    
    async with supabase_client_context() as supabase:
        # Get report
        report_response = await supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        if not report_response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found with ID: {report_id}"
            )
        
        report = report_response.data[0]
        
        # Get template if specified
        template = None
        if template_id or report.get("template_id"):
            template_id_to_use = str(template_id) if template_id else report["template_id"]
            template_response = await supabase.table("templates").select("*").eq("template_id", template_id_to_use).execute()
            if template_response.data:
                template = template_response.data[0]
        
        # Get associated files
        files = await get_report_files(report_id)
        
        # Generate report content
        content = await generate_report_text(
            files=files,
            additional_info=additional_info or "",
            template=template
        )
        
        # Update report
        await supabase.table("reports").update({
            "content": content,
            "status": "generated",
            "updated_at": "now()"
        }).eq("report_id", str(report_id)).execute()
        
        return {
            "report_id": str(report_id),
            "content": content,
            "status": "generated"
        }


@router.post("/reports/{report_id}/refine", response_model=APIResponse[RefineReportResponse])
@api_error_handler
async def refine_report(
    report_id: UUID4,
    request: RefineRequest,
    background_tasks: BackgroundTasks
):
    """
    Refine an existing report based on instructions
    
    Args:
        report_id: UUID of the report to refine
        request: RefineRequest with instructions
        background_tasks: FastAPI background tasks
        
    Returns:
        Standardized API response with refined report data
    """
    async with supabase_client_context() as supabase:
        # Get report
        report_response = await supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        if not report_response.data:
            raise HTTPException(status_code=404, detail="Report not found")
        
        report = report_response.data[0]
        
        # Refine content
        refined_content = await refine_report_text(
            original_content=report["content"],
            instructions=request.instructions
        )
        
        # Update report
        await supabase.table("reports").update({
            "content": refined_content,
            "status": "refined",
            "updated_at": "now()"
        }).eq("report_id", str(report_id)).execute()
                
    return {
        "report_id": str(report_id),
        "content": refined_content,
        "status": "refined"
    }


@router.post("/simple-test", response_model=APIResponse[SimpleTestResponse])
@api_error_handler
async def simple_test(data: Dict[str, Any]):
    """
    A very simple test endpoint to check routing
    
    Args:
        data: Any JSON data
        
    Returns:
        Standardized API response with test message
    """
    return {
        "message": "Simple test endpoint works!",
        "received": data
    }


@router.post("/analyze", response_model=APIResponse[AnalysisResponseSchema])
@api_error_handler
async def analyze_documents(request: AnalyzeRequest):
    """
    Analyze uploaded documents and extract key information.
    
    Args:
        request: AnalyzeRequest with document IDs and additional info
        
    Returns:
        Standardized API response with analysis results
    """
    document_ids = request.document_ids
    additional_info = request.additional_info
    
    # Create a temporary directory for processing
    tmp_dir = os.path.join(settings.UPLOAD_DIR, f"tmp_{str(uuid.uuid4())}")
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Get text from all documents
    document_text = ""
    for doc_id in document_ids:
        try:
            doc_path = await get_document_path(doc_id)
            if not doc_path or not os.path.exists(doc_path):
                continue
            
            # Extract text from the document
            doc_text = await extract_text_from_file(doc_path)
            if doc_text:
                document_text += f"\n--- Document: {os.path.basename(doc_path)} ---\n{doc_text}\n\n"
        except Exception as e:
            logger.error(f"Error extracting text from document {doc_id}: {str(e)}")
    
    if not document_text:
        logger.warning("No document text could be extracted")
        return {
            "findings": {},
            "suggestions": ["No text could be extracted from the provided documents"],
            "extracted_variables": {}
        }
    
    # Add additional information if provided
    if additional_info:
        document_text += f"\n--- Additional Information ---\n{additional_info}\n"
    
    # Use the template processor to analyze documents
    analysis_result = await template_processor.analyze_document_text(document_text)
            
    # Convert analysis result to a standard format
    analysis_data = {
        "findings": analysis_result.get("findings", {}),
        "suggestions": analysis_result.get("suggestions", []),
        "extracted_variables": analysis_result.get("extracted_variables", {})
    }
    
    # Clean up temporary directory
    try:
        shutil.rmtree(tmp_dir)
    except Exception as e:
        logger.warning(f"Error cleaning up temp directory: {str(e)}")
    
    return analysis_data


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
            file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
            if not file_record:
                logger.warning(f"File with ID {file_id} not found")
                continue
                
            # Verify file existence
            file_path = safe_path_join(settings.UPLOAD_DIR, file_record.file_path)
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


def get_report_directory(report_id: UUID4) -> Path:
    """
    Get the directory for a report's files.
    
    Args:
        report_id: UUID of the report
        
    Returns:
        Path to the report's directory
    """
    report_dir = Path(settings.UPLOAD_DIR) / str(report_id)
    report_dir.mkdir(exist_ok=True)
    return report_dir


async def _generate_and_save_report(
    system_message: str,
    prompt: str,
    report_id: UUID4,
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
            output_file = safe_path_join(report_dir, "report.md")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(generated_text)
                
            # Update the report record in the database using Supabase
            from utils.supabase_helper import create_supabase_client
            
            try:
                # Initialize Supabase client
                supabase = create_supabase_client()
                
                # Update the report record
                response = supabase.table("reports").update({
                    "content": generated_text,
                    "file_path": safe_path_join("reports", str(report_id), "report.md"),
                    "status": "completed"
                }).eq("id", report_id).execute()
                
                logger.info(f"Updated report record for ID: {report_id}")
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                
        else:
            logger.error(f"Unexpected API response format: {response}")
            
            # Update report status to failed using Supabase
            from utils.supabase_helper import create_supabase_client
            
            try:
                # Initialize Supabase client
                supabase = create_supabase_client()
                
                # Update the report status
                supabase.table("reports").update({
                    "status": "failed"
                }).eq("id", report_id).execute()
                
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                
    except Exception as e:
        logger.error(f"Error in _generate_and_save_report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update report status to failed using Supabase
        try:
            from utils.supabase_helper import create_supabase_client
            
            # Initialize Supabase client
            supabase = create_supabase_client()
            
            # Update the report status
            supabase.table("reports").update({
                "status": "failed"
            }).eq("id", report_id).execute()
            
        except Exception as db_error:
            logger.error(f"Database error when updating status: {str(db_error)}")


async def generate_preview(report_id: UUID4, report_path: Path) -> None:
    """
    Generate a preview for a report.
    
    Args:
        report_id: UUID of the report
        report_path: Path to the report file
    """
    try:
        await preview_service.generate_preview(report_id)
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating preview: {str(e)}"
        )


# Cleanup task to run periodically
@router.on_event("startup")
@router.on_event("shutdown")
async def cleanup_old_files():
    """Clean up old preview files on startup and shutdown."""
    preview_service.cleanup_old_previews()


@router.post("/reports/generate-docx", response_model=APIResponse[GenerateDocxResponse])
@api_error_handler
async def generate_report_docx(
    background_tasks: BackgroundTasks,
    report_id: UUID4,
    db: Session = Depends(get_db),
):
    """
    Generate a DOCX report from a report ID
    
    Args:
        report_id: UUID of the report
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Standardized API response with status and report ID
    """
    logger.info(f"Starting report generation for report ID: {report_id}")
    
    # Find the report in the database
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    # Generate the report
    # ...additional implementation code here...
    
    return {
        "status": "success", 
        "report_id": str(report_id)
    }


@router.post("/from-id", response_model=APIResponse[GenerateFromIdResponse])
@api_error_handler
async def generate_report_from_id(
    data: Dict[str, Any] = Body(...),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Generate report content based on report_id
    
    Args:
        data: Dictionary containing report_id and optional parameters
        current_user: Optional authenticated user
    
    Returns:
        Standardized API response with the generated report data
        
    Authentication:
        This endpoint uses optional authentication. When authenticated, user ownership
        of the report will be verified.
    """
    # Extract report_id from request
    if "report_id" not in data:
        raise HTTPException(
            status_code=400, 
            detail="report_id is required"
        )
        
    report_id = data["report_id"]
    
    # Extract any additional options from request
    options = {k: v for k, v in data.items() if k != "report_id"}
    
    async with supabase_client_context() as supabase:
        # Get report from database
        report_response = await supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        if not report_response.data:
            raise HTTPException(
                status_code=404, 
                detail=f"Report not found with ID: {report_id}"
            )
            
        report = report_response.data[0]
        
        # Get files associated with report
        files = await get_report_files(report_id)
        
        # Process and extract text from files
        document_text = ""
        for file in files:
            file_path = file.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    text = extract_text_from_file(file_path)
                    if text:
                        filename = os.path.basename(file_path)
                        document_text += f"\n--- Document: {filename} ---\n{text}\n\n"
                except Exception as e:
                    logger.error(f"Error extracting text from {file_path}: {str(e)}")
        
        if not document_text:
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from report files"
            )
            
        # Add any additional info if available
        if "additional_info" in report and report["additional_info"]:
            document_text += f"\n--- Additional Information ---\n{report['additional_info']}\n"
            
        # Generate the report content
        generated_content = await generate_report_text(document_text)
        
        # Update the report with the generated content
        await supabase.table("reports").update({
            "content": generated_content,
            "status": "generated",
            "generated_at": "now()"
        }).eq("report_id", str(report_id)).execute()
        
        return {
            "report_id": str(report_id),
            "content": generated_content,
            "status": "generated"
        }
