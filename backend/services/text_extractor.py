import logging
from pathlib import Path
from typing import Optional

import docx2txt
import PyPDF2
from aiofiles import open as aio_open

logger = logging.getLogger(__name__)

async def extract_text_from_file(file_path: str) -> str:
    """
    Extract text content from a file based on its type.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If file type is not supported
    """
    path = Path(file_path)
    file_type = path.suffix.lower()
    
    try:
        if file_type == ".txt":
            async with aio_open(path, "r", encoding="utf-8") as f:
                return await f.read()
                
        elif file_type == ".pdf":
            # PDF extraction needs to be synchronous due to PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() for page in reader.pages)
                
        elif file_type in (".doc", ".docx"):
            # docx2txt is synchronous
            return docx2txt.process(path)
            
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
    except Exception as e:
        logger.error(f"Error extracting text from {path}: {str(e)}")
        raise 