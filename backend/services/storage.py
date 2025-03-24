import os
from pathlib import Path
from typing import Optional

from config import settings
from utils.error_handler import logger


def get_document_path(document_id: str) -> str:
    """
    Get the file path for a document based on its ID.

    Args:
        document_id: The ID of the document

    Returns:
        The full path to the document file
    """
    upload_dir = Path(settings.UPLOAD_DIR)

    # Check if the document_id is a directory (for uploaded files)
    doc_dir = upload_dir / str(document_id)
    if doc_dir.is_dir():
        # Look for files in the document directory
        files = list(doc_dir.glob("*.*"))
        if files:
            # Return the first file (typically there's only one)
            return str(files[0])

        # Check if there's a metadata file that points to the file location
        metadata_path = doc_dir / "metadata.json"
        if metadata_path.exists():
            try:
                import json

                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    files = metadata.get("files", [])
                    if files and "path" in files[0]:
                        file_path = files[0]["path"]
                        if os.path.exists(file_path):
                            return file_path
            except Exception as e:
                logger.error(
                    f"Error reading metadata for document {document_id}: {str(e)}"
                )

    # Check if the document is in the reports directory
    reports_dir = upload_dir / "reports" / str(document_id)
    if reports_dir.is_dir():
        # Look for DOCX files
        docx_files = list(reports_dir.glob("*.docx"))
        if docx_files:
            return str(docx_files[0])

    # If document_id is a direct file path
    if os.path.exists(str(document_id)):
        return str(document_id)

    # Check the generated_reports directory
    generated_dir = Path("generated_reports")
    if generated_dir.exists():
        report_path = generated_dir / f"{document_id}.docx"
        if report_path.exists():
            return str(report_path)

    # Last resort: check if it's a DOCX file in the upload directory
    docx_path = upload_dir / f"{document_id}.docx"
    if docx_path.exists():
        return str(docx_path)

    logger.warning(f"Document not found with ID: {document_id}")
    return str(upload_dir / str(document_id))


def get_upload_path(filename: str, folder: Optional[str] = None) -> Path:
    """
    Get the path where a file should be uploaded.

    Args:
        filename: Name of the file to upload
        folder: Optional subfolder within the upload directory

    Returns:
        Path where the file should be stored
    """
    upload_dir = Path(settings.UPLOAD_DIR)

    if folder:
        directory = upload_dir / folder
    else:
        directory = upload_dir

    # Ensure the directory exists
    directory.mkdir(parents=True, exist_ok=True)

    return directory / filename


def list_files(directory: str) -> list:
    """
    List all files in a directory.

    Args:
        directory: Path to the directory to list

    Returns:
        List of file paths
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    return [str(file) for file in dir_path.glob("*.*") if file.is_file()]
