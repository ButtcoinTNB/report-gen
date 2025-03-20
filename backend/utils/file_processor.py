"""
Utility class for file processing operations.
Centralizes common file handling functionality to reduce code duplication.
"""

import os
import shutil
import mimetypes
import logging
from typing import Dict, List, Union, BinaryIO, Optional, Any
from pathlib import Path
from werkzeug.utils import secure_filename
import uuid
import tempfile
from PIL import Image
import magic
import base64
import re
import fitz
import docx
import docx2txt
import pytesseract

# Setup logging
logger = logging.getLogger(__name__)

class FileProcessor:
    """Unified file processing utilities to eliminate code duplication"""
    
    # Common MIME type groups
    TEXT_MIME_TYPES = [
        "text/plain", 
        "application/pdf", 
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    IMAGE_MIME_TYPES = [
        "image/jpeg", 
        "image/png", 
        "image/tiff", 
        "image/bmp", 
        "image/gif", 
        "image/webp"
    ]
    
    @staticmethod
    def get_mime_type(file_path: Union[str, Path]) -> str:
        """
        Get MIME type from file path
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type as string, defaults to "application/octet-stream" if not detected
        """
        # Initialize mimetypes if not already done
        if not mimetypes.inited:
            mimetypes.init()
            
        # Try to get MIME type from file extension first
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # If no MIME type found or it's generic, try using python-magic
        if not mime_type or mime_type == 'application/octet-stream':
            try:
                # Use python-magic if available for more accurate detection
                if os.path.exists(str(file_path)):
                    mime_type = magic.from_file(str(file_path), mime=True)
            except (ImportError, Exception) as e:
                logger.warning(f"Could not use magic for MIME detection: {str(e)}")
                
        # Fall back to a basic mapping if still not found
        if not mime_type:
            extension = os.path.splitext(str(file_path))[1].lower()
            mime_map = {
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif',
                '.csv': 'text/csv',
                '.json': 'application/json',
                '.xml': 'application/xml',
                '.html': 'text/html',
                '.htm': 'text/html'
            }
            mime_type = mime_map.get(extension, 'application/octet-stream')
            
        return mime_type
    
    @staticmethod
    def get_file_extension(file_path: Union[str, Path]) -> str:
        """
        Get file extension from file path
        
        Args:
            file_path: Path to the file
            
        Returns:
            File extension (lowercase) including the dot, e.g., ".pdf"
        """
        # Initialize mimetypes if not already done
        if not mimetypes.inited:
            mimetypes.init()
            
        # Get extension from MIME type
        extension = mimetypes.guess_extension(FileProcessor.get_mime_type(file_path))
        
        # Handle special cases and common MIME types
        mime_to_ext = {
            'text/plain': '.txt',
            'application/pdf': '.pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/tiff': '.tif',
            'image/bmp': '.bmp',
            'image/gif': '.gif',
            'text/csv': '.csv',
            'application/json': '.json',
            'application/xml': '.xml',
            'text/html': '.html'
        }
        
        if FileProcessor.get_mime_type(file_path) in mime_to_ext:
            return mime_to_ext[FileProcessor.get_mime_type(file_path)]
            
        return extension if extension else ""
    
    @staticmethod
    def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get comprehensive file information
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file details (name, size, type, etc.)
        """
        file_path_str = str(file_path)
        
        if not os.path.exists(file_path_str):
            return {
                'name': os.path.basename(file_path_str),
                'path': file_path_str,
                'exists': False,
                'size_bytes': 0,
                'size_mb': 0,
                'extension': '',
                'mime_type': 'application/octet-stream',
                'is_text': False,
                'is_binary': False,
                'is_image': False
            }
            
        path_obj = Path(file_path_str)
        filename = path_obj.name
        extension = path_obj.suffix.lower()
        
        # Get file stats
        stats = path_obj.stat()
        
        # Get MIME type
        mime_type = FileProcessor.get_mime_type(file_path_str)
        
        # Determine if text/binary/image
        is_text = FileProcessor.is_text_file(file_path_str)
        is_binary = not is_text
        is_image = FileProcessor.is_image_file(file_path_str)
        
        return {
            'name': filename,
            'path': file_path_str,
            'extension': extension,
            'directory': str(path_obj.parent),
            'size_bytes': stats.st_size,
            'size_mb': stats.st_size / (1024 * 1024),
            'mtime': stats.st_mtime,
            'ctime': stats.st_ctime,
            'mime_type': mime_type,
            'is_text': is_text,
            'is_binary': is_binary,
            'is_image': is_image,
            'exists': True
        }
    
    @staticmethod
    def is_text_file(file_path: Union[str, Path]) -> bool:
        """
        Check if file is a text-based document
        
        Args:
            file_path: Path to the file
            
        Returns:
            Boolean indicating if it's a text-based file
        """
        if not os.path.exists(str(file_path)):
            return False
            
        # Check if it's a known text file extension
        ext = os.path.splitext(str(file_path))[1].lower()
        if ext in ['.txt', '.csv', '.md', '.json', '.xml', '.html', '.htm', '.log', '.py', '.js', '.css']:
            return True
            
        # Try to read the file as text
        try:
            with open(str(file_path), 'r', encoding='utf-8') as check_file:
                check_file.read(1024)  # Try to read as text
                return True
        except UnicodeDecodeError:
            return False
        except Exception as e:
            logger.error(f"Error checking if file is text: {str(e)}")
            return False
    
    @staticmethod
    def is_image_file(file_path: Union[str, Path]) -> bool:
        """
        Check if file is an image
        
        Args:
            file_path: Path to the file
            
        Returns:
            Boolean indicating if it's an image file
        """
        if not os.path.exists(str(file_path)):
            return False
            
        # Check if it's a known image file extension
        ext = os.path.splitext(str(file_path))[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico']:
            # Try to open with PIL to confirm it's a valid image
            try:
                image = Image.open(str(file_path))
                image.verify()  # Verify it's an image
                return True
            except Exception:
                return False
                
        # Check MIME type
        mime_type = FileProcessor.get_mime_type(file_path)
        return mime_type in FileProcessor.IMAGE_MIME_TYPES
    
    @staticmethod
    def is_binary_file(file_path: Union[str, Path]) -> bool:
        """
        Check if file is binary by attempting to read as text
        
        Args:
            file_path: Path to the file
            
        Returns:
            Boolean indicating if it's a binary file
        """
        return not FileProcessor.is_text_file(file_path)
    
    @staticmethod
    def safe_path_join(base_dir: Union[str, Path], *paths) -> str:
        """
        Safely join paths to prevent directory traversal attacks
        
        Args:
            base_dir: Base directory to contain the result
            *paths: Path components to join
            
        Returns:
            Safe joined path as string
            
        Raises:
            ValueError if resulting path would be outside base_dir
        """
        base_path = Path(base_dir).resolve()
        joined_path = Path(base_dir).joinpath(*paths).resolve()
        
        # Ensure result is within the base directory
        if not str(joined_path).startswith(str(base_path)):
            # Instead of raising an error, sanitize the path
            # Remove any leading '..' path components
            sanitized_parts = []
            for part in paths:
                part_str = str(part)
                # Remove parent directory references and leading slashes
                part_str = re.sub(r'^[/\\]+', '', part_str)
                part_str = re.sub(r'\.+[/\\]', '', part_str)
                # On Windows, also remove drive specifiers
                if os.name == 'nt':
                    part_str = re.sub(r'^[a-zA-Z]:[/\\]', '', part_str)
                sanitized_parts.append(part_str)
            
            # Join sanitized parts
            return os.path.join(str(base_dir), *sanitized_parts)
        
        return str(joined_path)
    
    @staticmethod
    def save_upload(file: BinaryIO, directory: Union[str, Path], filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Save uploaded file with proper permissions and path validation
        
        Args:
            file: File-like object to save
            directory: Directory to save to
            filename: Optional filename to use (generates one if not provided)
            
        Returns:
            Dictionary with saved file information
            
        Raises:
            ValueError for invalid paths
            IOError for file saving failures
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(str(directory), exist_ok=True)
            
            # Generate filename if not provided
            if not filename:
                file_id = uuid.uuid4()
                if hasattr(file, 'filename'):
                    original_filename = secure_filename(getattr(file, 'filename'))
                    filename = f"{file_id}_{original_filename}"
                else:
                    filename = f"{file_id}_upload.bin"
            
            # Create safe path
            file_path = FileProcessor.safe_path_join(directory, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)
            
            # Get file info
            file_info = FileProcessor.get_file_info(file_path)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise IOError(f"Failed to save uploaded file: {str(e)}")
    
    @staticmethod
    def convert_image(input_path: Union[str, Path], output_path: Union[str, Path], format: Optional[str] = None) -> bool:
        """
        Convert image to another format for processing
        
        Args:
            input_path: Path to the image file
            output_path: Path to save the converted image
            format: Format to convert to (default: derived from output_path)
            
        Returns:
            Boolean indicating success
        """
        try:
            # Open the image
            image = Image.open(str(input_path))
            
            # Determine output format
            if not format:
                format = os.path.splitext(str(output_path))[1].lstrip('.')
                if format.lower() == 'jpg':
                    format = 'JPEG'
                    
            # Save the image in the new format
            image.save(output_path, format=format)
            logger.info(f"Converted {input_path} to {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error converting image: {str(e)}")
            return False
    
    @staticmethod
    def _detect_file_type(file_path: Union[str, Path]) -> Optional[str]:
        """
        Detect file type based on magic bytes
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected file extension or None if unknown
        """
        try:
            # Read first 16 bytes to check file signature
            with open(str(file_path), 'rb') as f:
                header = f.read(16)
                
            # Define file signatures for common file types
            signatures = {
                b'%PDF': '.pdf',
                b'\x50\x4B\x03\x04': '.docx',  # ZIP-based Office formats
                b'\xD0\xCF\x11\xE0': '.doc',   # OLE-based Office formats
                b'\xFF\xD8\xFF': '.jpg',
                b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': '.png',
                b'\x47\x49\x46\x38': '.gif',
                b'\x49\x49\x2A\x00': '.tif',  # TIFF (little endian)
                b'\x4D\x4D\x00\x2A': '.tif',  # TIFF (big endian)
                b'\x42\x4D': '.bmp'
            }
            
            # Check if the header matches any of the signatures
            for signature, ext in signatures.items():
                if header.startswith(signature):
                    return ext
            
            # Special case for WEBP
            if len(header) >= 12 and header[0:4] == b'RIFF' and header[8:12] == b'WEBP':
                return '.webp'
                
            return None
            
        except Exception as e:
            logger.error(f"Error detecting file type: {str(e)}")
            return None
    
    @staticmethod
    def _extract_text_from_pdf(file_path: Union[str, Path]) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text
        """
        try:
            doc = fitz.open(str(file_path))
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text()
                
            doc.close()
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return f"Error extracting text from PDF: {str(e)}"
    
    @staticmethod
    def _extract_text_from_docx(file_path: Union[str, Path]) -> str:
        """
        Extract text from DOCX file
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Extracted text
        """
        try:
            return docx2txt.process(str(file_path))
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            return f"Error extracting text from DOCX: {str(e)}"
    
    @staticmethod
    def _extract_text_from_image(file_path: Union[str, Path]) -> str:
        """
        Extract text from image using OCR
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Extracted text
        """
        try:
            image = Image.open(str(file_path))
            text = pytesseract.image_to_string(image)
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            return f"Error extracting text from image: {str(e)}"
    
    @staticmethod
    def extract_text(file_path: Union[str, Path]) -> str:
        """
        Extract text from file (unified method for all file types)
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text
        """
        file_path_str = str(file_path)
        
        if not os.path.exists(file_path_str):
            error_msg = f"File does not exist: {file_path_str}"
            logger.error(error_msg)
            return error_msg
            
        try:
            # Get file info for logging
            file_info = FileProcessor.get_file_info(file_path_str)
            logger.info(f"Extracting text from {file_info['name']} ({file_info['size_mb']:.2f} MB)")
            
            # Check if file is empty
            if file_info['size_bytes'] == 0:
                error_msg = f"File is empty: {file_info['name']}"
                logger.error(error_msg)
                return error_msg
            
            # Process based on file extension
            extension = file_info['extension'].lower()
            
            # Plain text files
            if extension == '.txt' or (file_info['is_text'] and extension not in ['.pdf', '.docx', '.doc']):
                with open(file_path_str, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return content
                
            # PDF files
            elif extension == '.pdf':
                return FileProcessor._extract_text_from_pdf(file_path_str)
                
            # Word documents
            elif extension in ['.docx', '.doc']:
                return FileProcessor._extract_text_from_docx(file_path_str)
                
            # Image files
            elif file_info['is_image']:
                return FileProcessor._extract_text_from_image(file_path_str)
                
            # Try to detect file type if extension is unknown
            else:
                detected_type = FileProcessor._detect_file_type(file_path_str)
                if detected_type:
                    logger.info(f"Detected file type {detected_type} for {file_path_str}")
                    
                    if detected_type == '.pdf':
                        return FileProcessor._extract_text_from_pdf(file_path_str)
                    elif detected_type in ['.docx', '.doc']:
                        return FileProcessor._extract_text_from_docx(file_path_str)
                    elif detected_type in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif', '.webp']:
                        return FileProcessor._extract_text_from_image(file_path_str)
                
                # Last resort: try as text
                try:
                    with open(file_path_str, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    logger.info(f"Read file as text: {file_path_str}")
                    return content
                except Exception:
                    return f"Unsupported file type for text extraction: {extension}"
                    
        except Exception as e:
            logger.error(f"Error extracting text from file {file_path_str}: {str(e)}")
            return f"Error extracting text: {str(e)}"
    
    @staticmethod
    def extract_text_from_files(file_paths: List[Union[str, Path]]) -> str:
        """
        Extract text from multiple files and combine
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Combined text from all files
        """
        all_text = []
        
        for file_path in file_paths:
            text = FileProcessor.extract_text(file_path)
            
            # Skip error messages
            if not text.startswith("Error:") and not text.startswith("File does not exist:"):
                all_text.append(text)
                
        combined_text = "\n\n==== NEXT DOCUMENT ====\n\n".join(all_text)
        logger.info(f"Extracted text from {len(all_text)} files")
        
        return combined_text
    
    @staticmethod
    def get_file_as_base64(file_path: Union[str, Path]) -> Optional[str]:
        """
        Get file as base64 encoded string with MIME type prefix
        
        Args:
            file_path: Path to the file
            
        Returns:
            Base64 encoded string with MIME type prefix or None if error
        """
        file_path_str = str(file_path)
        
        if not os.path.exists(file_path_str):
            logger.error(f"File not found for base64 encoding: {file_path_str}")
            return None
            
        try:
            # Get the MIME type
            mime_type = FileProcessor.get_mime_type(file_path_str)
            
            # Read and encode file
            with open(file_path_str, 'rb') as f:
                file_data = f.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')
                
            # Return with MIME type prefix
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"Error encoding file as base64: {str(e)}")
            return None
    
    @staticmethod
    def file_exists(file_path: Union[str, Path]) -> bool:
        """
        Check if a file exists
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file exists, False otherwise
        """
        return os.path.exists(str(file_path)) and os.path.isfile(str(file_path))
    
    @staticmethod
    def delete_file(file_path: Union[str, Path]) -> bool:
        """
        Delete a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if deletion was successful, False otherwise
        """
        file_path_str = str(file_path)
        
        try:
            if not os.path.exists(file_path_str):
                logger.warning(f"Cannot delete non-existent file: {file_path_str}")
                return False
                
            os.unlink(file_path_str)
            logger.info(f"Deleted file: {file_path_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_path_str}: {str(e)}")
            return False
    
    @staticmethod
    def copy_file(source_path: Union[str, Path], target_path: Union[str, Path]) -> bool:
        """
        Copy a file from source to target
        
        Args:
            source_path: Path to the source file
            target_path: Path to the target file
            
        Returns:
            True if copy was successful, False otherwise
        """
        source_str = str(source_path)
        target_str = str(target_path)
        
        try:
            if not os.path.exists(source_str):
                logger.warning(f"Cannot copy non-existent file: {source_str}")
                return False
                
            # Create target directory if it doesn't exist
            target_dir = os.path.dirname(target_str)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                
            shutil.copy2(source_str, target_str)
            logger.info(f"Copied file from {source_str} to {target_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file from {source_str} to {target_str}: {str(e)}")
            return False 