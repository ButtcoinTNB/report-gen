import fitz  # PyMuPDF
import os
import docx
import re
from typing import Dict, Any, List, Optional
from utils.error_handler import logger
import time


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
    Extract text from a DOCX file using multiple methods for maximum compatibility.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text or detailed error message
    """
    try:
        logger.info(f"Extracting text from DOCX file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return f"Error: File not found: {file_path}"
        
        # Get file size and basic details for debugging
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        logger.info(f"DOCX file details: Name={file_name}, Size={file_size} bytes")
        
        # If file is too small to be a valid DOCX, report it
        if file_size < 500:  # Minimum size for a valid DOCX
            logger.error(f"File too small to be a valid DOCX: {file_size} bytes")
            return f"Error: File too small to be a valid DOCX file (only {file_size} bytes)"
        
        # Try multiple methods to extract text, starting with the most reliable
        extraction_methods = [
            "python-docx",
            "zipfile-xml",
            "binary-analysis"
        ]
        
        all_errors = []
        for method in extraction_methods:
            try:
                logger.info(f"Trying {method} extraction method")
                
                if method == "python-docx":
                    # Method 1: Standard python-docx extraction
                    try:
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
                        table_count = len(doc.tables)
                        logger.info(f"DOCX contains {table_count} tables")
                        
                        for i, table in enumerate(doc.tables):
                            for row in table.rows:
                                row_text = []
                                for cell in row.cells:
                                    for paragraph in cell.paragraphs:
                                        text = paragraph.text.strip()
                                        if text:
                                            row_text.append(text)
                                if row_text:
                                    all_text.append(" | ".join(row_text))
                        
                        # Join all text with newlines
                        result = '\n'.join(all_text)
                        
                        # If we got text, return it
                        if result.strip():
                            logger.info(f"Successfully extracted {len(result)} characters using python-docx")
                            return result
                        else:
                            logger.warning("python-docx returned no text content")
                            all_errors.append("python-docx extracted no text content")
                    except Exception as e:
                        logger.error(f"python-docx extraction failed: {str(e)}")
                        all_errors.append(f"python-docx error: {str(e)}")
                        # Continue to next method
                
                elif method == "zipfile-xml":
                    # Method 2: Direct ZIP+XML extraction
                    try:
                        import zipfile
                        from xml.etree import ElementTree
                        
                        logger.info("Attempting extraction via zipfile+xml parsing")
                        
                        # DOCX files are zip files containing XML
                        text_content = []
                        with zipfile.ZipFile(file_path) as docx_zip:
                            # Check if it's actually a valid DOCX structure
                            if "word/document.xml" not in docx_zip.namelist():
                                logger.warning("No word/document.xml found in the DOCX file")
                                all_errors.append("Not a valid DOCX structure (missing document.xml)")
                                continue  # Try next method
                                
                            # Extract main document content
                            with docx_zip.open("word/document.xml") as content:
                                tree = ElementTree.parse(content)
                                for elem in tree.iter():
                                    # Look for text elements in the XML
                                    if elem.tag.endswith('}t') and elem.text:
                                        text_content.append(elem.text)
                            
                            # Also try to extract headers and footers which might contain text
                            header_footer_files = [f for f in docx_zip.namelist() 
                                                if f.startswith('word/header') or f.startswith('word/footer')]
                            
                            for hf_file in header_footer_files:
                                try:
                                    with docx_zip.open(hf_file) as content:
                                        tree = ElementTree.parse(content)
                                        for elem in tree.iter():
                                            if elem.tag.endswith('}t') and elem.text:
                                                text_content.append(elem.text)
                                except Exception as hf_error:
                                    logger.warning(f"Error extracting from {hf_file}: {str(hf_error)}")
                        
                        if text_content:
                            result = '\n'.join(text_content)
                            logger.info(f"Successfully extracted {len(result)} characters using zipfile+xml")
                            return result
                        else:
                            logger.warning("No text found in document.xml")
                            all_errors.append("No text found in document.xml")
                    except Exception as e:
                        logger.error(f"zipfile+xml extraction failed: {str(e)}")
                        all_errors.append(f"zipfile+xml error: {str(e)}")
                
                elif method == "binary-analysis":
                    # Method 3: Binary file analysis
                    try:
                        import zipfile
                        
                        # Check if file is a valid ZIP (all DOCXs must be valid ZIPs)
                        if not zipfile.is_zipfile(file_path):
                            logger.error(f"File is not a valid ZIP/DOCX file: {file_path}")
                            return f"Error: File is not a valid DOCX format. The file may be corrupted or in a different format."
                        
                        # Try to detect password protection
                        with open(file_path, 'rb') as f:
                            content = f.read(4000)  # Read start of file
                            if b'encryptedKey' in content or b'encryption' in content:
                                logger.error(f"DOCX file appears to be password-protected")
                                return "Error: This DOCX file appears to be password-protected. Please remove the password protection and try again."
                        
                        # Try to extract raw text using strings-like approach as last resort
                        try:
                            with open(file_path, 'rb') as f:
                                binary_content = f.read()
                                
                            # Try to find readable text fragments
                            import re
                            text_fragments = []
                            
                            # Look for potential text in the binary file
                            # Try different encodings
                            for encoding in ['utf-8', 'latin1', 'utf-16']:
                                try:
                                    decoded = binary_content.decode(encoding, errors='ignore')
                                    # Find sequences of readable characters
                                    words = re.findall(r'[A-Za-z0-9\s.,;:\'\"!?()-]{4,}', decoded)
                                    if words:
                                        text_fragments.extend(words)
                                except Exception:
                                    pass
                            
                            if text_fragments:
                                # Deduplicate and join fragments
                                unique_fragments = list(set(text_fragments))
                                result = '\n'.join(unique_fragments)
                                logger.info(f"Extracted {len(result)} characters using binary analysis")
                                return result
                        except Exception as bin_error:
                            logger.error(f"Binary analysis failed: {str(bin_error)}")
                            
                        # If we get here, it's likely a document with no text content
                        logger.error(f"All extraction methods failed for DOCX")
                        return "Error: Unable to extract text content from this DOCX file. The file may be image-based, contain no text, or use an unsupported format."
                    except Exception as e:
                        logger.error(f"DOCX analysis failed: {str(e)}")
                        all_errors.append(f"Analysis error: {str(e)}")
            
            except Exception as method_error:
                logger.error(f"Extraction method {method} failed with error: {str(method_error)}")
                all_errors.append(f"{method} error: {str(method_error)}")
                continue  # Try next method
        
        # If we get here, all methods failed
        error_details = "\n".join(all_errors)
        logger.error(f"All DOCX extraction methods failed: {error_details}")
        return f"Error: Failed to extract text from DOCX using multiple methods. File may be corrupted, password-protected, or contain no text content."
            
    except Exception as e:
        logger.error(f"Critical error in DOCX extraction: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text from DOCX: {str(e)}"


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


def extract_text_from_files(file_paths: List[str]) -> str:
    """
    Extract text from multiple files and combine the results.
    
    Args:
        file_paths: List of file paths
        
    Returns:
        Combined extracted text
    """
    if not file_paths:
        return "Error: No files provided for text extraction"
    
    # Track if we're using multimodal for any file
    used_multimodal = False
    multimodal_results = {}
    
    # First, try normal extraction for all files
    normal_results = []
    file_stats = {}
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            continue
        
        try:
            # Extract text using our standard methods
            file_name = os.path.basename(file_path)
            logger.info(f"Extracting text from file: {file_name}")
            start_time = time.time()
            
            extracted_text = extract_text_from_file(file_path)
            
            # Calculate extraction time and content size
            extraction_time = time.time() - start_time
            text_length = len(extracted_text) if extracted_text else 0
            
            # Store stats for logging and decision-making
            file_stats[file_path] = {
                'time': extraction_time,
                'length': text_length,
                'file_name': file_name,
                'extraction_success': not (extracted_text.startswith("Error:") or
                                          "Error extracting text" in extracted_text),
                'has_error_markers': any(marker in extracted_text for marker in 
                                       ["[OCR failed", "No readable text detected", "password-protected",
                                        "encrypted", "binary format", "Error extracting"])
            }
            
            logger.info(f"Extracted {text_length} characters in {extraction_time:.2f} seconds from {file_name}")
            
            # Add to our results
            normal_results.append(extracted_text)
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            normal_results.append(f"Error extracting text from {os.path.basename(file_path)}: {str(e)}")
    
    # Combine the normal extraction results
    combined_normal_text = "\n\n--- NEXT DOCUMENT ---\n\n".join(
        [text for text in normal_results if text]
    )
    
    # Calculate total extracted text length
    total_normal_length = len(combined_normal_text) if combined_normal_text else 0
    logger.info(f"Total extracted text length using normal methods: {total_normal_length} characters")
    
    # Check if we need to try multimodal extraction
    need_multimodal = False
    problem_files = []
    
    # Decision criteria for when to use multimodal:
    # 1. Very little text extracted overall
    if total_normal_length < 300:
        need_multimodal = True
        logger.warning(f"Very little text extracted ({total_normal_length} chars). Trying multimodal approach.")
    
    # 2. Files with extraction errors or minimal content
    for file_path, stats in file_stats.items():
        # Skip very small files which might legitimately have little content
        file_size_bytes = os.path.getsize(file_path)
        is_small_file = file_size_bytes < 1024  # Skip files smaller than 1KB
        
        if (not stats['extraction_success'] or 
            (stats['length'] < 100 and not is_small_file) or
            stats['has_error_markers']):
            problem_files.append(file_path)
    
    if problem_files:
        need_multimodal = True
        logger.warning(f"Found {len(problem_files)} files with extraction issues. Will try multimodal approach.")
    
    # Use multimodal extraction if needed and available
    if need_multimodal:
        try:
            # Import here to avoid circular imports
            from services.multimodal_processor import extract_text_with_multimodal
            import asyncio
            
            # Note we're using multimodal
            used_multimodal = True
            
            # Get event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If no event loop exists in the current context, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Process problem files with multimodal
            for file_path in problem_files:
                file_name = os.path.basename(file_path)
                logger.info(f"Trying multimodal extraction on {file_name}")
                
                # Run the async function in the event loop
                multimodal_text = loop.run_until_complete(extract_text_with_multimodal(file_path))
                
                # Store the result
                multimodal_results[file_path] = multimodal_text
                logger.info(f"Multimodal extraction returned {len(multimodal_text)} characters for {file_name}")
                
            # Replace the normal results with multimodal results for problem files
            final_results = []
            
            for file_path in file_paths:
                if file_path in multimodal_results:
                    # Use multimodal result for this file
                    result_text = multimodal_results[file_path]
                    # Add a marker to indicate multimodal was used
                    result_text = f"[Extracted using AI Vision technology]\n\n{result_text}"
                    final_results.append(result_text)
                else:
                    # Use normal extraction result
                    file_index = file_paths.index(file_path)
                    if file_index < len(normal_results):
                        final_results.append(normal_results[file_index])
            
            # Combine all results
            combined_text = "\n\n--- NEXT DOCUMENT ---\n\n".join(
                [text for text in final_results if text]
            )
            
            total_final_length = len(combined_text) if combined_text else 0
            logger.info(f"Final extracted text length (with multimodal): {total_final_length} characters")
            
            return combined_text
            
        except ImportError as ie:
            logger.warning(f"Multimodal extraction not available: {str(ie)}")
            logger.warning("Falling back to normal extraction results")
            return combined_normal_text
            
        except Exception as e:
            logger.error(f"Error during multimodal extraction: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("Falling back to normal extraction results")
            return combined_normal_text
    
    # If we didn't need multimodal, return the normal results
    return combined_normal_text


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
        from PIL import Image, ImageEnhance, ImageFilter
        
        logger.info(f"Extracting text from image file: {file_path}")
        file_name = os.path.basename(file_path)
        
        # Open the image
        image = Image.open(file_path)
        
        # Check for file size and dimensions
        width, height = image.size
        file_size = os.path.getsize(file_path)
        logger.info(f"Image dimensions: {width}x{height}, size: {file_size/1024:.2f} KB")
        
        # Preprocessing to improve OCR results
        try:
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
                
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Apply slight sharpening
            image = image.filter(ImageFilter.SHARPEN)
            
            # Remove noise using median filter for better OCR
            image = image.filter(ImageFilter.MedianFilter(3))
            
            logger.info("Successfully applied image preprocessing for better OCR")
        except Exception as preprocess_error:
            logger.warning(f"Image preprocessing error (continuing anyway): {str(preprocess_error)}")
        
        # Apply OCR with different settings to maximize text extraction
        ocr_results = []
        
        # Try default OCR
        try:
            default_text = pytesseract.image_to_string(image)
            if default_text:
                ocr_results.append(default_text)
                logger.info(f"Default OCR extracted {len(default_text)} characters")
        except Exception as default_error:
            logger.warning(f"Default OCR failed: {str(default_error)}")
            
        # Try with different configurations
        tesseract_configs = [
            '--psm 6',  # Assume a single uniform block of text
            '--psm 3 --oem 3',  # Default paragraph mode with LSTM
            '--psm 4'  # Assume a single column of text
        ]
        
        for config in tesseract_configs:
            try:
                config_text = pytesseract.image_to_string(image, config=config)
                if config_text and config_text not in ocr_results:
                    ocr_results.append(config_text)
                    logger.info(f"OCR with config '{config}' extracted {len(config_text)} characters")
            except Exception as config_error:
                logger.warning(f"OCR with config '{config}' failed: {str(config_error)}")
        
        # Combine results (if we got multiple successful extractions)
        if ocr_results:
            # Choose the longest text result as it's likely the most complete
            ocr_results.sort(key=len, reverse=True)
            text = ocr_results[0]
            
            if not text or text.strip() == "":
                logger.warning(f"No text extracted from image: {file_path}")
                return f"[No readable text detected in image: {file_name}]"
            
            logger.info(f"Successfully extracted {len(text)} characters from image")
            return text
        else:
            logger.warning(f"All OCR attempts failed for image: {file_path}")
            return f"[OCR failed to extract text from image: {file_name}]"
        
    except ImportError:
        logger.error("OCR libraries not installed (pytesseract, PIL)")
        return "Error: OCR libraries (pytesseract, PIL) not installed for image text extraction"
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text from image: {str(e)}"
