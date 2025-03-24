import os
import re
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from config import settings
from utils.error_handler import logger
from utils.file_processor import FileProcessor

# Configure Tesseract path if specified in settings
if hasattr(settings, "TESSERACT_CMD_PATH") and settings.TESSERACT_CMD_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD_PATH


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file, including headers and footers.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dictionary containing metadata, including headers and footers
    """
    metadata = {
        "headers": [],
        "footers": [],
        "page_count": 0,
        "title": "",
        "author": "",
        "creation_date": "",
    }

    try:
        logger.info(f"Extracting metadata from PDF: {file_path}")

        if not os.path.exists(file_path):
            logger.warning(f"PDF file not found: {file_path}")
            return metadata

        doc = fitz.open(file_path)

        # Log basic file info
        file_info = FileProcessor.get_file_info(file_path)
        logger.info(
            f"PDF opened successfully. Pages: {doc.page_count}, Size: {file_info['size_bytes']} bytes"
        )

        # Basic metadata
        metadata.update(
            {
                "page_count": doc.page_count,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
            }
        )

        logger.debug(f"Basic metadata extracted: {metadata}")

        # Extract potential headers and footers
        if doc.page_count > 0:
            # Try to identify headers and footers by examining first few pages
            headers = []
            footers = []

            # Process up to 3 pages or all pages if fewer
            pages_to_check = min(3, doc.page_count)
            logger.info(f"Analyzing {pages_to_check} pages for headers and footers")

            for page_num in range(pages_to_check):
                page = doc[page_num]
                text_blocks = page.get_text("blocks")

                logger.debug(f"Page {page_num+1}: Found {len(text_blocks)} text blocks")

                if text_blocks:
                    # First block often contains header
                    # Last block often contains footer
                    if text_blocks:
                        # Get first block text
                        first_block = text_blocks[0]
                        first_block_text = first_block[4]

                        # Add to headers if not yet included and not empty
                        if first_block_text.strip() and first_block_text not in headers:
                            # Remove metadata and clean up
                            clean_text = first_block_text.strip().split("\n")[0]
                            if (
                                clean_text and len(clean_text) < 100
                            ):  # Headers are typically short
                                headers.append(clean_text)
                                logger.debug(f"Found potential header: {clean_text}")

                        # Get last block text
                        last_block = text_blocks[-1]
                        last_block_text = last_block[4]

                        # Add to footers if not yet included and not empty
                        if last_block_text.strip() and last_block_text not in footers:
                            # Clean up and check if looks like a footer
                            clean_text = last_block_text.strip().split("\n")[-1]

                            # Check if it looks like a page number or footer
                            if clean_text and (
                                re.search(r"\d+\s*$", clean_text)  # Ends with a number
                                or "page" in clean_text.lower()
                                or "confidential" in clean_text.lower()
                                or "copyright" in clean_text.lower()
                                or len(clean_text) < 50  # Short text is likely a footer
                            ):
                                footers.append(clean_text)
                                logger.debug(f"Found potential footer: {clean_text}")

            # Add default page number footer if none found
            if not footers:
                footers.append("Page {page} of {total_pages}")
                logger.info("No footers detected, using default page numbering")

            # Update metadata with headers and footers
            metadata["headers"] = headers
            metadata["footers"] = footers

            # If no title in metadata but we found headers, use first header as title
            if not metadata["title"] and headers:
                metadata["title"] = headers[0]
                logger.info(f"Using header as title: {headers[0]}")

            logger.info(f"Extracted {len(headers)} headers and {len(footers)} footers")

    except Exception as e:
        logger.error(f"Error extracting PDF metadata from {file_path}: {str(e)}")
        logger.exception("PDF metadata extraction failed with exception")

    return metadata


def extract_text_from_file(file_path):
    """
    Extract text from a file, supporting different file formats including images.

    Args:
        file_path: Path to the file

    Returns:
        Extracted text or error message
    """
    # Use FileProcessor to extract text
    return FileProcessor.extract_text(file_path)


def detect_file_type(file_path: str) -> Optional[str]:
    """
    Detect the actual file type based on the file signature (magic bytes).

    Args:
        file_path: Path to the file

    Returns:
        Detected file extension with dot (e.g., '.pdf') or None if unknown
    """
    # Use the FileProcessor implementation to avoid code duplication
    return FileProcessor._detect_file_type(file_path)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file, with fallback to OCR for image-based PDFs.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text from the PDF
    """
    return FileProcessor._extract_text_from_pdf(file_path)


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file.

    Args:
        file_path: Path to the DOCX file

    Returns:
        Extracted text from the DOCX
    """
    return FileProcessor._extract_text_from_docx(file_path)


def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from a plain text file.

    Args:
        file_path: Path to the text file

    Returns:
        Text content from the file
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from TXT: {str(e)}")
        logger.exception("TXT text extraction failed")
        return ""


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from an image file using OCR.

    Args:
        file_path: Path to the image file

    Returns:
        Extracted text from the image
    """
    return FileProcessor._extract_text_from_image(file_path)


def extract_text_from_files(file_paths: List[str]) -> str:
    """
    Extract text from multiple files and combine the results.

    Args:
        file_paths: List of paths to files

    Returns:
        Combined extracted text from all files
    """
    return FileProcessor.extract_text_from_files(file_paths)


def extract_structured_data_from_text(text: str) -> Dict[str, Any]:
    """
    Extract structured data from text using pattern matching.
    This is a basic implementation that can be enhanced with more patterns.

    Args:
        text: Text to extract data from

    Returns:
        Dictionary of extracted data fields
    """
    structured_data = {}

    # Date patterns (various formats)
    date_patterns = [
        (r"Data\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", "data"),
        (r"Data sinistro\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", "data_sinistro"),
        (r"Emesso il\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", "data_emissione"),
    ]

    # Company/entity patterns
    company_patterns = [
        (r"Richiedente\s*:?\s*([^\n\r\t]+)", "richiedente"),
        (r"Assicurato\s*:?\s*([^\n\r\t]+)", "assicurato"),
        (r"Compagnia\s*:?\s*([^\n\r\t]+)", "compagnia"),
        (r"Contraente\s*:?\s*([^\n\r\t]+)", "contraente"),
    ]

    # Policy patterns
    policy_patterns = [
        (r"Polizza\s*(?:n\.?|numero)?\s*:?\s*([A-Za-z0-9\-\.\/]+)", "polizza"),
        (r"N\. polizza\s*:?\s*([A-Za-z0-9\-\.\/]+)", "polizza"),
    ]

    # Address patterns
    address_patterns = [
        (r"Indirizzo\s*:?\s*([^\n\r\t]+)", "indirizzo"),
        (
            r"Via\s+([^\n\r\t,]+),?\s*n\.?\s*(\d+)(?:[^\n\r\t]+)(?:,?\s*(\d{5}))?(?:\s*,?\s*([^\n\r\t]+))?",
            "indirizzo_completo",
        ),
    ]

    # Apply all patterns
    for pattern_group in [
        date_patterns,
        company_patterns,
        policy_patterns,
        address_patterns,
    ]:
        for pattern, key in pattern_group:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if key not in structured_data:  # Only capture first occurrence
                    if key == "indirizzo_completo":
                        # Combine address components
                        street = match.group(1)
                        number = match.group(2)
                        postal_code = match.group(3) if len(match.groups()) > 2 else ""
                        city = match.group(4) if len(match.groups()) > 3 else ""

                        structured_data["indirizzo"] = f"Via {street}, {number}"
                        if postal_code:
                            structured_data["cap"] = postal_code
                        if city:
                            structured_data["city"] = city
                    else:
                        structured_data[key] = match.group(1).strip()

    logger.info(f"Extracted {len(structured_data)} structured data fields from text")
    return structured_data
