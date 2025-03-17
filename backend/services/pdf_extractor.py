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


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text content from a file based on its extension.
    
    Args:
        file_path: Path to the file to extract text from
        
    Returns:
        Extracted text content
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return f"File not found: {file_path}"
    
    file_ext = os.path.splitext(file_path)[1].lower()
    file_size = os.path.getsize(file_path)
    
    logger.info(f"Extracting text from {file_path} (type: {file_ext}, size: {file_size} bytes)")
    
    # Extract text based on file type
    try:
        if file_ext == '.pdf':
            text = extract_text_from_pdf(file_path)
            logger.info(f"PDF extraction complete, extracted {len(text)} characters")
            return text
        elif file_ext in ['.docx', '.doc']:
            text = extract_text_from_docx(file_path)
            logger.info(f"DOCX extraction complete, extracted {len(text)} characters")
            return text
        elif file_ext == '.txt':
            text = extract_text_from_txt(file_path)
            logger.info(f"TXT extraction complete, extracted {len(text)} characters")
            return text
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            logger.info(f"Image file detected, no text extraction performed")
            return f"[Image file: {os.path.basename(file_path)}]"
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return f"Unsupported file type: {file_ext}"
    except Exception as e:
        error_msg = f"Error extracting text from {os.path.basename(file_path)}: {str(e)}"
        logger.error(error_msg)
        logger.exception("Text extraction failed with exception")
        return error_msg


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        logger.info(f"Opening PDF for text extraction: {file_path}")
        doc = fitz.open(file_path)
        
        logger.info(f"PDF has {doc.page_count} pages")
        for page_num in range(doc.page_count):
            page = doc[page_num]
            logger.debug(f"Extracting text from page {page_num + 1}")
            page_text = page.get_text()
            text += page_text
            text += f"\n--- Page {page_num + 1} ---\n"
            
            # Log the amount of text extracted from each page
            logger.debug(f"Page {page_num + 1}: Extracted {len(page_text)} characters")
            
            # Check if page appears to be empty
            if len(page_text.strip()) < 10:
                logger.warning(f"Page {page_num + 1} appears to have very little text")
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        logger.exception("PDF text extraction failed")
    
    logger.info(f"PDF extraction completed with {len(text)} total characters")
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    text = ""
    try:
        logger.info(f"Opening DOCX for text extraction: {file_path}")
        doc = docx.Document(file_path)
        paragraph_count = len(doc.paragraphs)
        logger.info(f"DOCX has {paragraph_count} paragraphs")
        
        for i, para in enumerate(doc.paragraphs):
            text += para.text + "\n"
            
            # Log every 50 paragraphs to avoid excessive logging
            if i % 50 == 0 or i == paragraph_count - 1:
                logger.debug(f"Processed {i+1}/{paragraph_count} paragraphs")
                
        logger.info(f"DOCX extraction completed with {len(text)} total characters")
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        logger.exception("DOCX text extraction failed")
    
    return text


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
    Extract text from multiple files and combine into a single text.
    
    Args:
        file_paths: List of file paths to extract text from
        
    Returns:
        Combined text from all files
    """
    combined_text = ""
    total_files = len(file_paths)
    successful_files = 0
    
    logger.info(f"Starting text extraction from {total_files} files")
    
    for i, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        logger.info(f"Processing file {i+1}/{total_files}: {filename}")
        
        try:
            file_text = extract_text_from_file(file_path)
            
            # Check if extraction was successful
            if not file_text.startswith("Error"):
                successful_files += 1
            
            combined_text += f"\n--- File: {filename} ---\n"
            combined_text += file_text
            combined_text += "\n\n"
        except Exception as e:
            error_msg = f"Failed to process {filename}: {str(e)}"
            logger.error(error_msg)
            combined_text += f"\n--- File: {filename} ---\n"
            combined_text += f"Error: {str(e)}\n\n"
    
    logger.info(f"Text extraction complete. Successfully processed {successful_files}/{total_files} files")
    logger.info(f"Combined text length: {len(combined_text)} characters")
    
    return combined_text
