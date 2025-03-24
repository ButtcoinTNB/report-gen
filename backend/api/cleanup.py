import logging
from pathlib import Path

from database.document import get_documents_by_report_id
from database.reports import get_report_by_id
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger("cleanup")

router = APIRouter(prefix="/api/cleanup", tags=["cleanup"])

# Directory where temporary files are stored
TEMP_DIR = Path("./temp_files")
UPLOAD_DIR = Path("./uploads")


class CleanupRequest(BaseModel):
    reportId: str


@router.post("/temp-files")
async def cleanup_temp_files(
    cleanup_request: CleanupRequest, background_tasks: BackgroundTasks
):
    """
    Clean up temporary files associated with a report ID

    This endpoint handles cleaning up any temporary files that were created
    during the report generation process. It runs in the background to avoid
    blocking the response.
    """
    report_id = cleanup_request.reportId

    if not report_id:
        raise HTTPException(status_code=400, detail="Report ID is required")

    # Schedule cleanup in the background
    background_tasks.add_task(_cleanup_files, report_id)

    return {"status": "success", "message": "Cleanup scheduled"}


async def _cleanup_files(report_id: str):
    """
    Perform the actual cleanup of temporary files

    This function is executed in the background and handles removing temporary
    files created during report generation and processing.
    """
    logger.info(f"Starting cleanup for report ID: {report_id}")

    try:
        # Fetch report and associated document IDs
        report = await get_report_by_id(report_id)
        if not report:
            logger.warning(f"Report not found for ID: {report_id}")
            return

        documents = await get_documents_by_report_id(report_id)
        document_ids = [doc.id for doc in documents]

        # Clean up temporary report files
        _remove_temp_files_by_pattern(f"{report_id}_*")

        # Clean up document files
        for doc_id in document_ids:
            _remove_temp_files_by_pattern(f"{doc_id}_*")

        logger.info(f"Completed cleanup for report ID: {report_id}")
    except Exception as e:
        logger.error(f"Error during cleanup for report ID {report_id}: {str(e)}")


def _remove_temp_files_by_pattern(pattern: str):
    """
    Remove files matching a pattern from the temp directory
    """
    # Check temp directory
    if TEMP_DIR.exists():
        for file_path in TEMP_DIR.glob(pattern):
            try:
                file_path.unlink()
                logger.info(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove temp file {file_path}: {str(e)}")

    # Check uploads directory
    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.glob(pattern):
            try:
                file_path.unlink()
                logger.info(f"Removed upload file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove upload file {file_path}: {str(e)}")
