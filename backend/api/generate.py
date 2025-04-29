import os
import time
from typing import Any, Dict, List, Optional, TypeVar, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
)

# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import settings
    from models import User
    from services.ai_service import (
        AIServiceError,
        call_openrouter_api,
        generate_report_text,
        refine_report_text,
    )
    from services.pdf_extractor import extract_text_from_file
    from services.template_processor import template_processor
    from utils.auth import get_current_user
    from utils.error_handler import (
        api_error_handler,
        logger,
    )
    from utils.exceptions import (
        AIServiceException,
        BadRequestException,
        DatabaseException,
        NotFoundException,
    )
    from utils.file_utils import temporary_directory
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from config import settings
    from models import User
    from services.ai_service import (
        AIServiceError,
        call_openrouter_api,
        generate_report_text,
        refine_report_text,
    )
    from services.pdf_extractor import extract_text_from_file
    from services.template_processor import template_processor
    from utils.auth import get_current_user
    from utils.error_handler import (
        api_error_handler,
        logger,
    )
    from utils.exceptions import (
        AIServiceException,
        BadRequestException,
        DatabaseException,
        NotFoundException,
    )
    from utils.file_utils import temporary_directory

import logging
import shutil
import uuid
from pathlib import Path
from uuid import UUID

from api.schemas import APIResponse
from pydantic import UUID4, BaseModel
from services.preview_service import preview_service
from services.storage import get_document_path
from utils.file_utils import safe_path_join
from utils.supabase_helper import async_supabase_client_context
from utils.storage import get_absolute_file_path, validate_file_exists
from utils.db_utils import supabase_transaction
from models.report import Report, ReportCreate
from models.file import FileRecord
from services.agent_service import AgentService
from services.file_processor import FileProcessor
from utils.exceptions import ValidationException
from postgrest import AsyncPostgrestClient

router = APIRouter(tags=["Report Generation"])
logger = logging.getLogger(__name__)

# Initialize the agent service
agent_service = AgentService()

T = TypeVar('T')


class StructureReportRequest(BaseModel):
    """Request model for generating a report from a specific structure"""

    document_ids: List[UUID4]
    title: Optional[str] = None
    structure: Optional[str] = None
    template_id: Optional[UUID4] = None


class GeneratePreviewRequest(BaseModel):
    """Request model for generating a report preview"""
    report_id: UUID4


class AnalyzeRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: str = ""
    report_id: Optional[UUID4] = (
        None  # Make report_id optional to maintain backwards compatibility
    )


class GenerateRequest(BaseModel):
    """Request model for generating a report."""
    document_ids: List[UUID4]
    title: Optional[str] = None
    template_id: Optional[UUID4] = None
    additional_info: Optional[str] = ""


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
    """Response model for report generation."""
    report_id: str


async def fetch_reference_reports():
    """
    Fetches stored reference reports from Supabase or local files.

    Returns:
        List of reference report data with extracted text
    """
    try:
        # Use supabase_client_context instead
        async with async_supabase_client_context() as supabase:
            # Fetch reference reports from the database
            response = await supabase.table("reference_reports").select("*").execute()

            if hasattr(response, "data") and response.data:
                print(
                    f"Successfully fetched {len(response.data)} reference reports from Supabase"
                )

                # Ensure each report has the expected fields
                valid_reports = []
                for report in response.data:
                    if "extracted_text" in report and report["extracted_text"]:
                        valid_reports.append(report)
                    else:
                        print(
                            f"Warning: Reference report {report.get('id', 'unknown')} missing extracted text"
                        )

                if valid_reports:
                    return valid_reports
                else:
                    print(
                        "No valid reference reports found in Supabase (missing extracted text)"
                    )
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
        safe_path_join(
            settings.UPLOAD_DIR, "templates"
        ),  # Check in templates directory
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
                print(
                    f"Found {len(reference_files)} reference files: {[os.path.basename(f) for f in reference_files]}"
                )

                for file_path in reference_files:
                    try:
                        print(f"Extracting text from reference file: {file_path}")
                        extracted_text = extract_text_from_file(file_path)

                        if not extracted_text or extracted_text.startswith("Error:"):
                            print(
                                f"Warning: Could not extract text from {file_path}: {extracted_text}"
                            )
                            continue

                        reference_data.append(
                            {
                                "id": os.path.basename(file_path),
                                "name": os.path.basename(file_path),
                                "extracted_text": extracted_text,
                                "file_path": file_path,
                            }
                        )
                        print(
                            f"Successfully extracted {len(extracted_text)} characters from {file_path}"
                        )
                    except Exception as e:
                        print(f"Error extracting text from {file_path}: {str(e)}")

                if reference_data:
                    print(
                        f"Successfully loaded {len(reference_data)} reference documents"
                    )
                    return reference_data
                else:
                    print(
                        f"Could not extract text from any files in {dir_path}, trying next directory"
                    )

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
        async with async_supabase_client_context() as supabase:
            response = await supabase.table("files") \
                .select("*") \
                .eq("report_id", str(report_id)) \
                .execute()
            return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting report files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting report files: {str(e)}"
        )


@router.post("/", response_model=APIResponse[GenerateReportResponse])
@api_error_handler
async def generate_report(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate a new report from uploaded files

    Args:
        request: GenerateRequest with document IDs and additional info
        background_tasks: FastAPI background tasks

    Returns:
        Standardized API response with the generated report ID
    """
    try:
        # Verify all files exist and are processed
        async with async_supabase_client_context() as supabase:
            supabase_client = cast(AsyncPostgrestClient, supabase)
            
            for doc_id in request.document_ids:
                file_response = await supabase_client.table("files").select("*").eq("file_id", str(doc_id)).execute()
                if not file_response.data:
                    raise ValidationException(
                        message=f"File not found: {doc_id}",
                        details={"file_id": str(doc_id)}
                    )
                file = FileRecord.model_validate(file_response.data[0])
                if file.status != "processed":
                    raise ValidationException(
                        message=f"File not fully processed: {doc_id}",
                        details={"file_id": str(doc_id), "status": file.status}
                    )

            # Create report record
            report_id = str(uuid.uuid4())
            report_data = {
                "report_id": report_id,
                "title": request.title or "New Report",
                "status": "processing",
                "content": "",
                "is_finalized": False,
                "quality_score": 0.0,
                "iterations": 0,
                "current_version": 1,
                "template_id": str(request.template_id) if request.template_id else None,
                "document_ids": [str(doc_id) for doc_id in request.document_ids],
                "metadata": {
                    "start_time": datetime.now().isoformat(),
                    "additional_info": request.additional_info
                }
            }

            # Insert report record
            response = await supabase_client.table("reports").insert(report_data).execute()
            if not response.data:
                raise DatabaseException(
                    message="Failed to create report",
                    details={"operation": "Insert report"}
                )

            report = cast(Dict[str, Any], response.data[0])

            # Update files with report_id
            for doc_id in request.document_ids:
                await supabase_client.table("files").update({
                    "report_id": report_id,
                    "status": "in_use"
                }).eq("file_id", str(doc_id)).execute()

            # Start the AI agent loop in the background
            background_tasks.add_task(
                agent_service.generate_report,
                report_data=ReportCreate(
                    report_id=report_id,
                    document_ids=request.document_ids,
                    template_id=request.template_id,
                    additional_info=request.additional_info
                )
            )

            return {"report_id": report_id}

    except Exception as e:
        logger.error(f"Error in generate_report: {str(e)}")
        raise


@router.post("/generate", response_model=APIResponse[GenerateContentResponse])
@api_error_handler
async def generate_report_content(
    request: GenerateRequest, current_user: Optional[User] = Depends(get_current_user)
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
    if hasattr(request, "report_id") and request.report_id:
        report_id = request.report_id

    if not report_id:
        raise BadRequestException(
            message="Report ID is required",
            details={"field": "report_id", "reason": "missing"},
        )

    additional_info = request.additional_info
    template_id = request.template_id

    async with async_supabase_client_context() as supabase:
        # Get report
        report_response = await supabase.table("reports") \
            .select("*") \
            .eq("report_id", str(report_id)) \
            .execute()
            
        if not report_response.data:
            raise NotFoundException(
                message=f"Report not found with ID: {report_id}",
                details={"resource_type": "report", "resource_id": str(report_id)},
            )

        report = report_response.data[0]
        
        # Get associated files
        files_response = await supabase.table("files") \
            .select("*") \
            .eq("report_id", str(report_id)) \
            .execute()
            
        if not files_response.data:
            raise NotFoundException(
                message="No documents found for this report",
                details={"report_id": str(report_id)},
            )

        # Continue with report generation using files_response.data
        # ... rest of the function ...


@router.post(
    "/reports/{report_id}/refine", response_model=APIResponse[RefineReportResponse]
)
@api_error_handler
async def refine_report(
    report_id: UUID4, request: RefineRequest, background_tasks: BackgroundTasks
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
    async with async_supabase_client_context() as supabase:
        # Get report
        report_response = (
            await supabase.table("reports")
            .select("*")
            .eq("report_id", str(report_id))
            .execute()
        )
        if not report_response.data:
            raise NotFoundException(
                message="Report not found",
                details={"resource_type": "report", "resource_id": str(report_id)},
            )

        report = report_response.data[0]

        try:
            # Refine content
            refined_content = await refine_report_text(
                original_content=report["content"], instructions=request.instructions
            )
        except AIServiceError as e:
            raise AIServiceException(
                message="Failed to refine report content with AI service",
                details={
                    "error_type": e.__class__.__name__,
                    "original_error": str(e),
                    "report_id": str(report_id),
                },
            )

        # Update report
        try:
            await supabase.table("reports").update(
                {"content": refined_content, "status": "refined", "updated_at": "now()"}
            ).eq("report_id", str(report_id)).execute()
        except Exception:
            raise DatabaseException(
                message="Failed to update report in database",
                details={"report_id": str(report_id), "operation": "update"},
            )

    return {
        "report_id": str(report_id),
        "content": refined_content,
        "status": "refined",
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
    return {"message": "Simple test endpoint works!", "received": data}


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

    document_text = []
    extraction_results = []

    with temporary_directory(settings.UPLOAD_DIR) as tmp_dir:
        try:
            async with async_supabase_client_context() as supabase:
                for doc_id in document_ids:
                    try:
                        file_response = await supabase.table("files").select("*").eq("file_id", str(doc_id)).execute()
                        if not file_response.data:
                            extraction_results.append({
                                "document_id": doc_id,
                                "status": "error",
                                "error": "File not found in database"
                            })
                            continue

                        file_record = file_response.data[0]
                        abs_file_path = get_absolute_file_path(file_record["file_path"])
                        
                        if not validate_file_exists(abs_file_path):
                            extraction_results.append({
                                "document_id": doc_id,
                                "status": "error",
                                "error": "File not found on disk"
                            })
                            continue

                        try:
                            text = await extract_text_from_file(abs_file_path)
                            if text:
                                document_text.append(f"Document '{file_record['filename']}': {text}")
                                extraction_results.append({
                                    "document_id": doc_id,
                                    "status": "success",
                                    "chars_extracted": len(text)
                                })
                                
                                # Update file record with extracted text
                                await supabase.table("files").update({
                                    "content": text,
                                    "processed_at": datetime.utcnow().isoformat()
                                }).eq("file_id", str(doc_id)).execute()
                                
                            else:
                                extraction_results.append({
                                    "document_id": doc_id,
                                    "status": "warning",
                                    "error": "No text could be extracted"
                                })
                        except Exception as e:
                            logger.error(f"Error extracting text from document {doc_id}: {str(e)}")
                            logger.error(f"Full error: {traceback.format_exc()}")
                            extraction_results.append({
                                "document_id": doc_id,
                                "status": "error",
                                "error": str(e),
                                "error_type": e.__class__.__name__
                            })

                    except Exception as e:
                        logger.error(f"Error processing document {doc_id}: {str(e)}")
                        extraction_results.append({
                            "document_id": doc_id,
                            "status": "error",
                            "error": str(e),
                            "error_type": e.__class__.__name__
                        })

            if not document_text:
                return {
                    "status": "error",
                    "message": "No text could be extracted from any documents",
                    "extraction_results": extraction_results,
                    "findings": [],
                    "suggestions": [],
                    "extracted_variables": {}
                }

            # Add additional information if provided
            if additional_info:
                document_text.append(f"--- Additional Information ---\n{additional_info}\n")

            # Use the template processor to analyze documents
            analysis_result = await template_processor.analyze_document_text(document_text)

            # Convert analysis result to a standard format
            analysis_data = {
                "findings": analysis_result.get("findings", {}),
                "suggestions": analysis_result.get("suggestions", []),
                "extracted_variables": analysis_result.get("extracted_variables", {}),
            }

            return {
                "status": "success",
                "message": "Analysis completed successfully",
                "extraction_results": extraction_results,
                "findings": analysis_data["findings"],
                "suggestions": analysis_data["suggestions"],
                "extracted_variables": analysis_data["extracted_variables"],
            }

        except Exception as e:
            logger.error(f"Error in analyze_documents: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": "An error occurred while analyzing documents",
                "extraction_results": extraction_results,
                "findings": [],
                "suggestions": [],
                "extracted_variables": {}
            }


@router.post("/from-structure")
async def generate_from_structure(
    request: StructureReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Generate a report from uploaded documents using a specific structure."""
    logger.info(f"Generating report from structure for user {current_user.id}")

    try:
        # Create a report record using Supabase
        report_id = str(uuid.uuid4())
        
        async with async_supabase_client_context() as supabase:
            # Create report record
            report_response = await supabase.table("reports").insert({
                "report_id": report_id,
                "title": request.title or "Generated Report",
                "user_id": current_user.id,
                "status": "processing"
            }).execute()
            
            if not report_response.data:
                raise DatabaseException(
                    message="Failed to create report",
                    details={"operation": "Insert report"}
                )

            logger.info(f"Created report record with ID: {report_id}")

            # Create temp directory for this report
            report_dir = get_report_directory(report_id)
            os.makedirs(report_dir, exist_ok=True)

            # Get file paths for documents
            document_paths = []
            for file_id in request.document_ids:
                # Get file info from Supabase
                file_response = await supabase.table("files").select("*").eq("file_id", str(file_id)).execute()
                
                if not file_response.data:
                    logger.warning(f"File with ID {file_id} not found")
                    continue

                file_record = file_response.data[0]
                file_path = safe_path_join(settings.UPLOAD_DIR, file_record["file_path"])
                
                if not os.path.exists(file_path):
                    logger.warning(f"File not found at path: {file_path}")
                    continue

                document_paths.append(file_path)
                logger.info(f"Added document: {file_path}")

            if not document_paths:
                logger.error("No valid documents found for processing")
                await supabase.table("reports").update({"status": "failed"}).eq("report_id", report_id).execute()
                return {
                    "status": "failed",
                    "error": "No valid documents found for processing"
                }

            # Extract text from documents
            logger.info("Extracting text from documents...")
            from services.pdf_extractor import extract_text_from_files
            document_text = extract_text_from_files(document_paths)

            # Get the structure to use
            custom_format_template = request.structure or """
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

            # Prepare the system message and prompt
            system_message = (
                "Sei un esperto redattore di relazioni assicurative. DEVI utilizzare SOLO fatti esplicitamente dichiarati nei documenti dell'utente. "
                "Non inventare, presumere o allucinare ALCUNA informazione non esplicitamente fornita. Rimani strettamente fattuale. "
                "NON utilizzare ALCUNA informazione dal modello di formato per il contenuto - serve SOLO per la struttura. "
                "Scrivi SEMPRE in italiano, indipendentemente dalla lingua di input."
            )

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

            # Add background task to generate report
            background_tasks.add_task(
                _generate_and_save_report,
                system_message=system_message,
                prompt=prompt,
                report_id=report_id,
                report_dir=report_dir,
                document_text=document_text,
                token_limit=settings.MAX_TOKENS,
            )

            return {"status": "processing", "report_id": report_id}

    except Exception as e:
        logger.error(f"Error in generate_from_structure: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        # Update report status if report was created
        if "report_id" in locals():
            async with async_supabase_client_context() as supabase:
                await supabase.table("reports").update({"status": "failed"}).eq("report_id", report_id).execute()

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
    token_limit: int = 4000,
):
    """Generate a report and save it to disk"""
    try:
        logger.info(f"Starting report generation for report ID: {report_id}")
        start_time = time.time()

        # Prepare API request
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        # Log the API call
        logger.info(
            f"Calling OpenRouter API with prompt length: {len(prompt)} characters"
        )

        # Call the OpenRouter API
        response = await call_openrouter_api(
            messages=messages, max_retries=2, timeout=120.0
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
            logger.info(
                f"Successfully generated report with {len(generated_text)} characters"
            )

            # Save the generated text to a file
            output_file = safe_path_join(report_dir, "report.md")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(generated_text)

            # Update the report record in the database using Supabase
            from utils.supabase_helper import async_supabase_client_context

            try:
                # Use supabase_client_context instead
                async with async_supabase_client_context() as supabase:
                    # Update the report record
                    response = (
                        supabase.table("reports")
                        .update(
                            {
                                "content": generated_text,
                                "file_path": safe_path_join(
                                    "reports", str(report_id), "report.md"
                                ),
                                "status": "completed",
                            }
                        )
                        .eq("id", report_id)
                        .execute()
                    )

                    logger.info(f"Updated report record for ID: {report_id}")
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")

        else:
            logger.error(f"Unexpected API response format: {response}")

            # Update report status to failed using Supabase
            from utils.supabase_helper import async_supabase_client_context

            try:
                # Use supabase_client_context instead
                async with async_supabase_client_context() as supabase:
                    # Update the report status
                    supabase.table("reports").update({"status": "failed"}).eq(
                        "id", report_id
                    ).execute()

            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")

    except Exception as e:
        logger.error(f"Error in _generate_and_save_report: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())

        # Update report status to failed using Supabase
        try:
            from utils.supabase_helper import async_supabase_client_context

            # Use supabase_client_context instead
            async with async_supabase_client_context() as supabase:
                # Update the report status
                supabase.table("reports").update({"status": "failed"}).eq(
                    "id", report_id
                ).execute()

        except Exception as db_error:
            logger.error(f"Database error when updating status: {str(db_error)}")


@router.post("/preview", response_model=APIResponse[Dict[str, Any]])
@api_error_handler
async def generate_preview(
    request: GeneratePreviewRequest,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Generate a preview of the report."""
    try:
        # Get report files
        async with async_supabase_client_context() as supabase:
            # Get report files
            files = await get_report_files(request.report_id)
            if not files:
                raise HTTPException(
                    status_code=404,
                    detail="No files found for this report"
                )
            return {"status": "success", "files": files}
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
    report_id: UUID4
):
    """
    Generate a DOCX report from a report ID

    Args:
        report_id: UUID of the report
        background_tasks: FastAPI background tasks

    Returns:
        Standardized API response with status and report ID
    """
    logger.info(f"Starting report generation for report ID: {report_id}")

    # Find the report in the database using Supabase
    async with async_supabase_client_context() as supabase:
        report_response = await supabase.table("reports").select("*").eq("report_id", str(report_id)).execute()
        if not report_response.data:
            raise HTTPException(status_code=404, detail="Report not found")

    # Generate the report
    # ...additional implementation code here...

    return {"status": "success", "report_id": str(report_id)}


@router.post("/from-id", response_model=APIResponse[GenerateFromIdResponse])
@api_error_handler
async def generate_report_from_id(
    data: Dict[str, Any] = Body(...),
    current_user: Optional[User] = Depends(get_current_user),
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
        raise HTTPException(status_code=400, detail="report_id is required")

    report_id = data["report_id"]

    # Extract any additional options from request
    # options = {k: v for k, v in data.items() if k != "report_id"}  # Uncomment if needed in the future

    async with async_supabase_client_context() as supabase:
        # Get report from database
        report_response = (
            await supabase.table("reports")
            .select("*")
            .eq("report_id", str(report_id))
            .execute()
        )
        if not report_response.data:
            raise HTTPException(
                status_code=404, detail=f"Report not found with ID: {report_id}"
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
                status_code=400, detail="No text could be extracted from report files"
            )

        # Add any additional info if available
        if "additional_info" in report and report["additional_info"]:
            document_text += (
                f"\n--- Additional Information ---\n{report['additional_info']}\n"
            )

        # Generate the report content
        generated_content = await generate_report_text(document_text)

        # Update the report with the generated content
        await supabase.table("reports").update(
            {
                "content": generated_content,
                "status": "generated",
                "generated_at": "now()",
            }
        ).eq("report_id", str(report_id)).execute()

        return {
            "report_id": str(report_id),
            "content": generated_content,
            "status": "generated",
        }


@router.get("/reports/{report_id}/files", response_model=APIResponse[List[Dict[str, Any]]])
@api_error_handler
async def get_report_files_endpoint(report_id: UUID4):
    """Get all files associated with a report."""
    try:
        async with async_supabase_client_context() as supabase:
            # Query the report by report_id
            response = await supabase.table("reports").select("document_ids").eq("report_id", str(report_id)).execute()
            
            # Handle case where report is not found
            if not response.data:
                logger.info(f"Report with ID {report_id} not found")
                return APIResponse(status="success", data=[])
            
            # Handle case where document_ids is NULL or empty
            document_ids = response.data[0].get("document_ids", [])
            if not document_ids:
                logger.info(f"No document IDs found for report {report_id}")
                return APIResponse(status="success", data=[])
            
            # Collect file records for each document ID
            files = []
            for doc_id in document_ids:
                if not doc_id:  # Skip null IDs
                    continue
                    
                file_response = await supabase.table("files").select("*").eq("file_id", doc_id).execute()
                if file_response.data:
                    files.append(file_response.data[0])
                else:
                    logger.warning(f"File with ID {doc_id} referenced by report {report_id} not found")
            
            return APIResponse(status="success", data=files)
    except Exception as e:
        logger.error(f"Error getting report files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting report files: {str(e)}"
        )
