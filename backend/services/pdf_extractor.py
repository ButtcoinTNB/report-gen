import fitz  # PyMuPDF
import os
import docx
import re
from typing import Dict, Any, List, Optional
from utils.error_handler import logger
import time
import pytesseract
from PIL import Image
import docx2txt
import io
from config import settings

# Configure Tesseract path if specified in settings
if hasattr(settings, 'TESSERACT_CMD_PATH') and settings.TESSERACT_CMD_PATH:
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
    Extract text from a file, supporting different file formats including images.
    
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
        file_name = os.path.basename(file_path)
        
        logger.info(f"Extracting text from {file_name} ({file_size_mb:.2f} MB, {file_extension})")
        
        # Check if file is empty
        if file_size_bytes == 0:
            error_msg = f"File is empty: {file_name}"
            logger.error(error_msg)
            return error_msg
        
        # Check for file signature (magic bytes) to determine actual file type
        file_type = detect_file_type(file_path)
        if file_type and file_type != file_extension:
            logger.info(f"File extension is {file_extension} but actual type appears to be {file_type}")
            
            # Prepare to handle the file based on its actual type instead of extension
            if file_type == '.pdf':
                logger.info(f"Processing as PDF despite extension {file_extension}")
                return extract_text_from_pdf(file_path)
            elif file_type in ['.docx', '.doc', '.xlsx', '.pptx']:
                logger.info(f"Processing as Office document despite extension {file_extension}")
                return extract_text_from_docx(file_path)
            elif file_type in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
                logger.info(f"Processing as image despite extension {file_extension}")
                return extract_text_from_image(file_path)
            
        # Try to detect if file is binary or text
        is_binary = False
        try:
            with open(file_path, 'r', encoding='utf-8') as check_file:
                check_file.read(1024)  # Try to read as text
        except UnicodeDecodeError:
            is_binary = True
            logger.info(f"File appears to be binary: {file_path}")
        
        # Process based on file extension or detected type
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc', '.docm', '.dot', '.dotx']:
            # Improved handling for Microsoft Word documents
            logger.info(f"Processing document file: {file_name}")
            return extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            logger.info(f"Processing text file: {file_name}")
            return extract_text_from_txt(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
            # Image files - use OCR
            logger.info(f"Processing image file: {file_name}")
            return extract_text_from_image(file_path)
        elif file_extension in ['.webp', '.heic', '.heif', '.jfif']:
            # Handle newer image formats by converting to PNG and then using OCR
            logger.info(f"Processing modern image format: {file_extension}")
            try:
                from PIL import Image
                import tempfile
                
                # Create a temporary PNG file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_png_path = temp_file.name
                
                # Open and convert the image
                image = Image.open(file_path)
                image.save(temp_png_path, 'PNG')
                logger.info(f"Converted {file_extension} to PNG for processing")
                
                # Extract text using our image function
                result = extract_text_from_image(temp_png_path)
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_png_path)
                except:
                    pass
                    
                return result
            except Exception as convert_error:
                logger.error(f"Error converting image format: {str(convert_error)}")
                return f"Error: Unable to process {file_extension} image format: {str(convert_error)}"
        else:
            # Unknown extension - try to detect what it might be
            logger.info(f"Unknown file extension: {file_extension}, attempting detection")
            
            # Check if it's a binary file
            if is_binary:
                logger.info("Attempting to process unknown binary file")
                
                # Try to detect various binary formats
                with open(file_path, 'rb') as f:
                    header = f.read(12)  # Read first 12 bytes
                    
                # Check for image file signatures
                if any(header.startswith(sig) for sig in [
                    b'\xFF\xD8\xFF',  # JPEG
                    b'\x89\x50\x4E\x47',  # PNG
                    b'\x47\x49\x46',  # GIF
                    b'\x49\x49\x2A\x00',  # TIFF
                    b'\x4D\x4D\x00\x2A',  # TIFF
                ]):
                    logger.info("File appears to be an image based on signature")
                    try:
                        from PIL import Image
                        # Try to open as image to confirm
                        Image.open(file_path)
                        return extract_text_from_image(file_path)
                    except Exception as img_error:
                        logger.warning(f"Failed to process as image: {str(img_error)}")
                
                # Check for Office document signatures
                elif header.startswith(b'\x50\x4B\x03\x04'):  # ZIP signature (DOCX/XLSX/PPTX)
                    logger.info("File appears to be an Office Open XML format")
                    return extract_text_from_docx(file_path)
                elif header.startswith(b'\xD0\xCF\x11\xE0'):  # OLE compound document (DOC/XLS/PPT)
                    logger.info("File appears to be a legacy Office format")
                    return extract_text_from_docx(file_path)
                elif header.startswith(b'%PDF'):  # PDF signature
                    logger.info("File appears to be a PDF based on signature")
                    return extract_text_from_pdf(file_path)
                
                # Try as image as a last resort for binary files
                try:
                    logger.info("Attempting to process as image as last resort")
                    from PIL import Image
                    # Try to open as image
                    Image.open(file_path)
                    return extract_text_from_image(file_path)
                except Exception:
                    pass
                    
                return f"Error: The file {file_name} is in a binary format that could not be identified for text extraction."
            else:
                # Not binary, try as plain text
                logger.info("File appears to be text-based, attempting to read as text")
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as text_file:
                        content = text_file.read()
                    logger.info(f"Successfully read {len(content)} characters from file as text")
                    return content
                except Exception as text_error:
                    logger.error(f"Failed to read as text: {str(text_error)}")
                    return f"Error: Failed to read {file_name} as text: {str(text_error)}"
        
    except Exception as e:
        logger.error(f"Error extracting text from file {file_path}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text: {str(e)}"


def detect_file_type(file_path: str) -> Optional[str]:
    """
    Detect the actual file type based on the file signature (magic bytes).
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected file extension with dot (e.g., '.pdf') or None if unknown
    """
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return None
    
    try:
        # Read first 16 bytes to check file signature
        with open(file_path, 'rb') as f:
            header = f.read(16)
            
        # Define file signatures for common file types
        signatures = {
            b'%PDF': '.pdf',
            b'\x50\x4B\x03\x04': '.docx',  # Also applies to .xlsx, .pptx, etc. (ZIP-based Office formats)
            b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': '.doc',  # Also applies to .xls, .ppt, etc. (OLE-based Office formats)
            b'\xFF\xD8\xFF': '.jpg',
            b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': '.png',
            b'\x47\x49\x46\x38': '.gif',
            b'\x49\x49\x2A\x00': '.tif',  # TIFF (little endian)
            b'\x4D\x4D\x00\x2A': '.tif',  # TIFF (big endian)
            b'\x52\x49\x46\x46': '.webp',  # RIFF marker, additional check needed
            b'\x42\x4D': '.bmp',
            b'RIFF....WEBP': '.webp',  # Replace .... with any 4 characters
        }
        
        # Check if the header matches any of the signatures
        for signature, ext in signatures.items():
            # For WEBP special case
            if signature == b'RIFF....WEBP' and len(header) >= 12:
                if header[0:4] == b'RIFF' and header[8:12] == b'WEBP':
                    return ext
            # For regular signatures
            elif header.startswith(signature):
                return ext
                
        # If we're here, the file type couldn't be determined from signatures
        # Try some additional checks
        
        # Check if it's a text file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                
            # Check for common text file markers
            if first_line.startswith('<!DOCTYPE html>') or first_line.startswith('<html'):
                return '.html'
            elif first_line.startswith('<?xml'):
                return '.xml'
            elif first_line.startswith('{') and file_path.endswith('.json'):
                return '.json'
            elif file_path.endswith('.txt'):
                return '.txt'
                
        except UnicodeDecodeError:
            # Not a text file
            pass
            
        # No match found
        return None
        
    except Exception as e:
        logger.error(f"Error detecting file type: {str(e)}")
        return None


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using PyMuPDF with fallback to OCR.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text from the PDF
    """
    try:
        logger.info(f"Extracting text from PDF: {file_path}")
        pdf_text = ""
        
        # Try PyMuPDF first for text layer extraction
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Try to get text from text layer
            text = page.get_text()
            
            # If text layer is empty or very short, try OCR
            if not text or len(text.strip()) < 50:  # Arbitrary threshold
                logger.info(f"Page {page_num} has little or no text, using OCR")
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
                img_data = pix.tobytes("png")
                
                # Use OCR on the image
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img, lang='ita+eng')
                pdf_text += page_text + "\n\n"
            else:
                pdf_text += text + "\n\n"
        
        doc.close()
        logger.info(f"Successfully extracted {len(pdf_text)} characters from PDF")
        
        return pdf_text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text from PDF: {str(e)}"


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text from the DOCX
    """
    try:
        logger.info(f"Extracting text from DOCX: {file_path}")
        
        # Use docx2txt to extract text
        text = docx2txt.process(file_path)
        
        logger.info(f"Successfully extracted {len(text)} characters from DOCX")
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        return f"Error extracting text from DOCX: {str(e)}"


def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from a plain text file.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Text content from the file
    """
    try:
        logger.info(f"Reading text file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
            
        logger.info(f"Successfully read {len(text)} characters from text file")
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
    try:
        logger.info(f"Extracting text from image: {file_path}")
        
        # Open the image
        img = Image.open(file_path)
        
        # Use pytesseract for OCR
        # Try Italian first, then English as fallback
        text = pytesseract.image_to_string(img, lang='ita+eng')
        
        logger.info(f"Successfully extracted {len(text)} characters from image")
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text from image: {str(e)}"


def extract_text_from_files(file_paths: List[str]) -> str:
    """
    Extract text from multiple files and combine them.
    
    Args:
        file_paths: List of file paths
        
    Returns:
        Combined extracted text from all files
    """
    try:
        logger.info(f"Extracting text from {len(file_paths)} files")
        
        all_text = []
        
        for file_path in file_paths:
            file_text = extract_text_from_file(file_path)
            
            # Skip error messages
            if not file_text.startswith("Error:"):
                all_text.append(file_text)
                
        combined_text = "\n\n==== NEXT DOCUMENT ====\n\n".join(all_text)
        
        logger.info(f"Successfully extracted {len(combined_text)} characters from all files")
        return combined_text
        
    except Exception as e:
        logger.error(f"Error extracting text from files: {str(e)}")
        return f"Error extracting text from files: {str(e)}"


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
        (r"Emesso il\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", "data_emissione")
    ]
    
    # Company/entity patterns
    company_patterns = [
        (r"Richiedente\s*:?\s*([^\n\r\t]+)", "richiedente"),
        (r"Assicurato\s*:?\s*([^\n\r\t]+)", "assicurato"),
        (r"Compagnia\s*:?\s*([^\n\r\t]+)", "compagnia"),
        (r"Contraente\s*:?\s*([^\n\r\t]+)", "contraente")
    ]
    
    # Policy patterns
    policy_patterns = [
        (r"Polizza\s*(?:n\.?|numero)?\s*:?\s*([A-Za-z0-9\-\.\/]+)", "polizza"),
        (r"N\. polizza\s*:?\s*([A-Za-z0-9\-\.\/]+)", "polizza")
    ]
    
    # Address patterns
    address_patterns = [
        (r"Indirizzo\s*:?\s*([^\n\r\t]+)", "indirizzo"),
        (r"Via\s+([^\n\r\t,]+),?\s*n\.?\s*(\d+)(?:[^\n\r\t]+)(?:,?\s*(\d{5}))?(?:\s*,?\s*([^\n\r\t]+))?", "indirizzo_completo")
    ]
    
    # Apply all patterns
    for pattern_group in [date_patterns, company_patterns, policy_patterns, address_patterns]:
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
