import fitz  # PyMuPDF
import os
import docx
import re
from typing import Dict, Any, List, Optional
from utils.error_handler import logger


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
        "creation_date": ""
    }
    
    try:
        logger.info(f"Extracting metadata from PDF: {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"PDF file not found: {file_path}")
            return metadata
            
        doc = fitz.open(file_path)
        
        # Log basic file info
        logger.info(f"PDF opened successfully. Pages: {doc.page_count}, Size: {os.path.getsize(file_path)} bytes")
        
        # Basic metadata
        metadata.update({
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
        })
        
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
                            clean_text = first_block_text.strip().split('\n')[0]
                            if clean_text and len(clean_text) < 100:  # Headers are typically short
                                headers.append(clean_text)
                                logger.debug(f"Found potential header: {clean_text}")
                        
                        # Get last block text
                        last_block = text_blocks[-1]
                        last_block_text = last_block[4]
                        
                        # Add to footers if not yet included and not empty
                        if last_block_text.strip() and last_block_text not in footers:
                            # Clean up and check if looks like a footer
                            clean_text = last_block_text.strip().split('\n')[-1]
                            
                            # Check if it looks like a page number or footer
                            if clean_text and (
                                re.search(r'\d+\s*$', clean_text) or  # Ends with a number
                                'page' in clean_text.lower() or
                                'confidential' in clean_text.lower() or
                                'copyright' in clean_text.lower() or
                                len(clean_text) < 50  # Short text is likely a footer
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
    Extract text from a file, supporting different file formats.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text or error message
    """
    if not os.path.exists(file_path):
        error_msg = f"File does not exist: {file_path}"
        logger.error(error_msg)
        return error_msg
        
    try:
        # Get file size for logging
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Get file extension and log file info
        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()
        
        logger.info(f"Extracting text from {file_path} ({file_size_mb:.2f} MB, {file_extension})")
        
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            # Make sure python-docx is installed
            try:
                import docx
                if file_extension == '.docx':
                    return extract_text_from_docx(file_path)
                else:
                    # For older .doc files, log a warning about potential issues
                    logger.warning(f"Processing .doc file which may have limited compatibility: {file_path}")
                    try:
                        # Try to use docx for .doc files (might work for some)
                        return extract_text_from_docx(file_path)
                    except Exception as doc_e:
                        logger.error(f"Failed to extract .doc with docx: {str(doc_e)}")
                        return f"Error: Failed to extract text from .doc file. Please convert it to .docx: {str(doc_e)}"
            except ImportError:
                logger.error("python-docx module not installed, cannot extract text from Word documents")
                return "Error: python-docx module not installed, cannot extract text from Word documents"
        elif file_extension == '.txt':
            return extract_text_from_txt(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            # For image files, log a message about OCR capabilities
            logger.info(f"Processing image file: {file_path}")
            try:
                # If pytesseract is installed, use OCR, otherwise return an error
                import pytesseract
                from PIL import Image
                return extract_text_from_image(file_path)
            except ImportError:
                logger.warning("pytesseract not installed, cannot extract text from images")
                return "Image file detected. OCR (text extraction from images) is not currently available."
        else:
            error_msg = f"Unsupported file type: {file_extension} for file {file_path}"
            logger.warning(error_msg)
            return error_msg
    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text: {str(e)}"


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file with detailed error handling.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or error message
    """
    try:
        import pdfplumber
        
        logger.info(f"Extracting text from PDF file: {file_path}")
        
        if not os.path.exists(file_path):
            error_msg = f"PDF file not found: {file_path}"
            logger.error(error_msg)
            return error_msg
            
        # Check if file size is 0
        if os.path.getsize(file_path) == 0:
            error_msg = f"PDF file is empty (0 bytes): {file_path}"
            logger.error(error_msg)
            return error_msg
        
        # Try to open the PDF
        try:
            with pdfplumber.open(file_path) as pdf:
                # Check if PDF is empty
                if len(pdf.pages) == 0:
                    error_msg = "PDF has no pages"
                    logger.warning(error_msg)
                    return error_msg
                
                logger.info(f"PDF has {len(pdf.pages)} pages")
                
                extracted_text = []
                for i, page in enumerate(pdf.pages):
                    try:
                        # Extract text from the page
                        page_text = page.extract_text() or ""
                        extracted_text.append(page_text)
                        
                        # Log progress periodically
                        if i % 5 == 0 or i == len(pdf.pages) - 1:
                            logger.info(f"Processed page {i+1}/{len(pdf.pages)}")
                            
                    except Exception as page_error:
                        # Log error but continue with other pages
                        logger.error(f"Error extracting text from page {i+1}: {str(page_error)}")
                        extracted_text.append(f"[Error extracting text from page {i+1}: {str(page_error)}]")
                
                # Combine text from all pages
                full_text = "\n\n".join(extracted_text)
                
                if not full_text.strip():
                    logger.warning(f"No text was extracted from the PDF (possibly scanned or image-based): {file_path}")
                    return f"[No text content could be extracted from the PDF, it may be scanned or image-based: {os.path.basename(file_path)}]"
                
                logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
                return full_text
                
        except Exception as pdf_error:
            error_msg = f"Error opening PDF: {str(pdf_error)}"
            logger.error(error_msg)
            
            # Check for common PDF errors
            error_str = str(pdf_error).lower()
            if "password" in error_str or "encrypted" in error_str or "decrypt" in error_str:
                return "Error: This PDF is password-protected. Please remove the password and try again."
            elif "stream" in error_str or "xref" in error_str or "startxref" in error_str:
                return "Error: This PDF file appears to be corrupted. Please try repairing or recreating the file."
            elif "pdf header" in error_str:
                return "Error: Not a valid PDF file. Please check the file format."
            else:
                return f"Error opening PDF: {str(pdf_error)}"
                
    except ImportError:
        logger.error("pdfplumber module not installed")
        return "Error: pdfplumber module not installed, cannot extract text from PDF"
    except Exception as e:
        logger.error(f"Unexpected error in PDF extraction: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text from PDF: {str(e)}"


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text
    """
    try:
        logger.info(f"Extracting text from DOCX file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return f"Error: File not found: {file_path}"
        
        try:
            # Try to open the DOCX file
            doc = docx.Document(file_path)
            
            # Log the number of paragraphs for debugging
            paragraph_count = len(doc.paragraphs)
            logger.info(f"DOCX contains {paragraph_count} paragraphs")
            
            # Extract text from each paragraph
            all_text = []
            for i, para in enumerate(doc.paragraphs):
                text = para.text.strip()
                if text:  # Only add non-empty paragraphs
                    all_text.append(text)
                
                # Log progress periodically to avoid excessive logging
                if i > 0 and i % 50 == 0:
                    logger.info(f"Processed {i}/{paragraph_count} paragraphs")
            
            # Also extract text from tables which might contain important information
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            text = paragraph.text.strip()
                            if text:
                                all_text.append(text)
            
            # Join all text with newlines
            result = '\n'.join(all_text)
            logger.info(f"Successfully extracted {len(result)} characters from {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error extracting text from DOCX: {str(e)}"
            
    except ImportError as e:
        logger.error(f"Python-docx library not installed: {str(e)}")
        return "Error: Python-docx library not installed"


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a TXT file."""
    try:
        logger.info(f"Opening TXT file for text extraction: {file_path}")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            text = file.read()
        logger.info(f"TXT extraction completed with {len(text)} total characters")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from TXT: {str(e)}")
        logger.exception("TXT text extraction failed")
        return ""


def extract_text_from_files(file_paths, max_chars=None):
    """
    Extract text from multiple files, handling different file types.
    
    Args:
        file_paths: List of paths to files
        max_chars: Optional maximum character limit for extracted text
        
    Returns:
        Combined extracted text from all files
    """
    try:
        logger.info(f"Extracting text from {len(file_paths)} files")
        
        # Check if we received any files
        if not file_paths or len(file_paths) == 0:
            error_message = "No files provided for text extraction"
            logger.error(error_message)
            return error_message
        
        all_texts = []
        results = {}
        
        for file_path in file_paths:
            if not file_path or not os.path.exists(file_path):
                error_msg = f"File not found or invalid path: {file_path}"
                logger.error(error_msg)
                results[file_path] = {"error": error_msg, "text": ""}
                all_texts.append(f"[Error: File not found or invalid path: {file_path}]")
                continue
                
            try:
                # Extract text from the file
                logger.info(f"Extracting text from file: {file_path}")
                text = extract_text_from_file(file_path)
                
                if not text or text.strip() == "":
                    error_msg = f"No text was extracted from: {file_path}"
                    logger.warning(error_msg)
                    text = f"[Empty content from file: {os.path.basename(file_path)}]"
                
                # Store the result
                results[file_path] = {"text": text, "size": len(text)}
                all_texts.append(text)
                
            except Exception as e:
                error_msg = f"Error extracting text from {file_path}: {str(e)}"
                logger.error(error_msg)
                logger.exception("Extraction error details:")
                results[file_path] = {"error": str(e), "text": ""}
                all_texts.append(f"[Error extracting text from {os.path.basename(file_path)}: {str(e)}]")
        
        # Combine the extracted text
        combined_text = "\n\n----------------\n\n".join(all_texts)
        
        # Check if any text was extracted
        if not combined_text or combined_text.strip() == "":
            error_msg = "No text was extracted from any of the provided files"
            logger.error(error_msg)
            return error_msg
            
        # Optionally limit the text length
        if max_chars and len(combined_text) > max_chars:
            logger.info(f"Limiting extracted text from {len(combined_text)} to {max_chars} characters")
            combined_text = combined_text[:max_chars] + f"\n\n[Text truncated to {max_chars} characters]"
            
        logger.info(f"Successfully extracted {len(combined_text)} characters from {len(file_paths)} files")
        
        # Add a summary of the extraction results
        extraction_summary = "\n\n--- Extraction Summary ---\n"
        for path, result in results.items():
            if "error" in result:
                extraction_summary += f"\nFile {os.path.basename(path)}: ERROR - {result['error']}"
            else:
                extraction_summary += f"\nFile {os.path.basename(path)}: {result['size']} characters extracted"
                
        # Add the summary at the end, but ensure it's within limit if max_chars is set
        if max_chars and len(combined_text) + len(extraction_summary) > max_chars:
            # Skip the summary if it would exceed the limit
            return combined_text
        else:
            return combined_text + extraction_summary
            
    except Exception as e:
        logger.error(f"Error in extract_text_from_files: {str(e)}")
        logger.exception("Full extraction error:")
        return f"Error extracting text from files: {str(e)}"


def extract_text_from_image(file_path):
    """
    Extract text from an image file using OCR.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Extracted text
    """
    try:
        import pytesseract
        from PIL import Image
        
        logger.info(f"Extracting text from image file: {file_path}")
        
        # Open the image
        image = Image.open(file_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        if not text or text.strip() == "":
            logger.warning(f"No text extracted from image: {file_path}")
            return f"[No text detected in image: {os.path.basename(file_path)}]"
        
        logger.info(f"Successfully extracted {len(text)} characters from image")
        return text
        
    except ImportError as e:
        logger.error(f"OCR libraries not installed: {str(e)}")
        return "Error: OCR libraries (pytesseract, PIL) not installed"
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text from image: {str(e)}"
