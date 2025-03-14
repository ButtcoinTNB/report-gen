import fitz  # PyMuPDF
import os
import docx
import re
from typing import Dict, Any, List, Optional


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
        doc = fitz.open(file_path)
        
        # Basic metadata
        metadata.update({
            "page_count": doc.page_count,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
        })
        
        # Extract potential headers and footers
        if doc.page_count > 0:
            # Try to identify headers and footers by examining first few pages
            headers = []
            footers = []
            
            # Process up to 3 pages or all pages if fewer
            pages_to_check = min(3, doc.page_count)
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                text_blocks = page.get_text("blocks")
                
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
            
            # Add default page number footer if none found
            if not footers:
                footers.append("Page {page} of {total_pages}")
                
            # Update metadata with headers and footers
            metadata["headers"] = headers
            metadata["footers"] = footers
            
            # If no title in metadata but we found headers, use first header as title
            if not metadata["title"] and headers:
                metadata["title"] = headers[0]
        
    except Exception as e:
        print(f"Error extracting PDF metadata from {file_path}: {str(e)}")
    
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
        return f"File not found: {file_path}"
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Extract text based on file type
    try:
        if file_ext == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            return extract_text_from_txt(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            return f"[Image file: {os.path.basename(file_path)}]"
        else:
            return f"Unsupported file type: {file_ext}"
    except Exception as e:
        return f"Error extracting text from {os.path.basename(file_path)}: {str(e)}"


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text()
            text += f"\n--- Page {page_num + 1} ---\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
    
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error extracting text from DOCX: {str(e)}")
    
    return text


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        print(f"Error extracting text from TXT: {str(e)}")
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
    
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        file_text = extract_text_from_file(file_path)
        
        combined_text += f"\n--- File: {filename} ---\n"
        combined_text += file_text
        combined_text += "\n\n"
    
    return combined_text
