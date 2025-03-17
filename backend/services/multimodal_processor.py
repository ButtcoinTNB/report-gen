import os
import base64
import logging
import tempfile
import time
from typing import List, Dict, Any, Optional, Tuple
import json
import requests
from PIL import Image
from config import settings
import fitz  # PyMuPDF for PDF handling

# Set up logging
logger = logging.getLogger(__name__)

# Maximum number of pages to process to avoid excessive API usage
MAX_PAGES = 10

def convert_document_to_images(file_path: str, output_dir: Optional[str] = None) -> List[str]:
    """
    Convert document (PDF, DOCX) to a series of images (one per page)
    
    Args:
        file_path: Path to the document file
        output_dir: Optional directory to save images (uses temp dir if None)
        
    Returns:
        List of paths to the generated images
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []
        
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Create temporary directory if not provided
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix="doc_images_")
    
    image_paths = []
    
    try:
        if file_ext == '.pdf':
            return convert_pdf_to_images(file_path, output_dir)
        elif file_ext in ['.docx', '.doc', '.rtf', '.odt']:
            return convert_docx_to_images(file_path, output_dir)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']:
            # For images, just copy to output dir with a standardized name
            output_path = os.path.join(output_dir, f"image_page_001{file_ext}")
            try:
                # Use Pillow to open and resave to ensure it's valid and convert if needed
                img = Image.open(file_path)
                img.save(output_path)
                image_paths.append(output_path)
                logger.info(f"Copied and converted image to {output_path}")
            except Exception as img_err:
                logger.error(f"Error processing image file: {str(img_err)}")
        else:
            logger.warning(f"Unsupported file type for multimodal: {file_ext}")
            
    except Exception as e:
        logger.error(f"Error converting document to images: {str(e)}")
    
    return image_paths

def convert_pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
    """
    Convert a PDF document to a series of images
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images
        
    Returns:
        List of paths to the generated images
    """
    image_paths = []
    
    try:
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        # Process each page (up to MAX_PAGES)
        max_pages = min(pdf_document.page_count, MAX_PAGES)
        logger.info(f"Converting {max_pages} pages from PDF {pdf_path}")
        
        for page_num in range(max_pages):
            try:
                # Get the page
                page = pdf_document[page_num]
                
                # Convert to image (pixmap)
                pix = page.get_pixmap(dpi=300)  # Higher DPI for better quality
                
                # Save the image
                image_path = os.path.join(output_dir, f"pdf_page_{page_num + 1:03d}.png")
                pix.save(image_path)
                
                # Add to list of image paths
                image_paths.append(image_path)
                logger.info(f"Converted PDF page {page_num + 1} to {image_path}")
                
            except Exception as page_error:
                logger.error(f"Error converting PDF page {page_num + 1}: {str(page_error)}")
                continue
                
        # Close the PDF document
        pdf_document.close()
        
    except Exception as e:
        logger.error(f"Error in PDF to image conversion: {str(e)}")
    
    return image_paths

def convert_docx_to_images(docx_path: str, output_dir: str) -> List[str]:
    """
    Convert a DOCX document to a series of images
    
    Args:
        docx_path: Path to the DOCX file
        output_dir: Directory to save images
        
    Returns:
        List of paths to the generated images
    """
    image_paths = []
    
    # Create a temporary PDF path
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        temp_pdf_path = tmp_file.name
    
    try:
        # Try to convert DOCX to PDF first using LibreOffice (if available)
        convert_success = False
        
        try:
            # Using LibreOffice for conversion
            import subprocess
            logger.info(f"Attempting to convert DOCX to PDF using LibreOffice: {docx_path}")
            
            # Check if LibreOffice is available
            result = subprocess.run(['which', 'libreoffice'], capture_output=True, text=True)
            
            if result.returncode == 0:
                libreoffice_path = result.stdout.strip()
                logger.info(f"LibreOffice found at {libreoffice_path}")
                
                # Use LibreOffice to convert DOCX to PDF
                cmd = [
                    'libreoffice', 
                    '--headless', 
                    '--convert-to', 'pdf', 
                    '--outdir', os.path.dirname(temp_pdf_path),
                    docx_path
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode == 0:
                    # LibreOffice puts the PDF in the same directory as the DOCX
                    converted_pdf = os.path.join(
                        os.path.dirname(temp_pdf_path),
                        os.path.basename(docx_path).replace('.docx', '.pdf')
                    )
                    
                    # If file exists, move/rename it to our temp path
                    if os.path.exists(converted_pdf):
                        import shutil
                        shutil.move(converted_pdf, temp_pdf_path)
                        convert_success = True
                        logger.info(f"Successfully converted DOCX to PDF using LibreOffice: {temp_pdf_path}")
                    else:
                        logger.warning(f"LibreOffice conversion completed but PDF not found at {converted_pdf}")
                else:
                    logger.warning(f"LibreOffice conversion failed: {process.stderr}")
            else:
                logger.warning("LibreOffice not found, trying alternative conversion methods")
                
        except Exception as lo_error:
            logger.warning(f"Error using LibreOffice for conversion: {str(lo_error)}")
            
        # If LibreOffice method failed, try using docx2pdf
        if not convert_success:
            try:
                from docx2pdf import convert as docx2pdf_convert
                logger.info(f"Attempting to convert DOCX to PDF using docx2pdf: {docx_path}")
                
                # Convert using docx2pdf
                docx2pdf_convert(docx_path, temp_pdf_path)
                
                if os.path.exists(temp_pdf_path) and os.path.getsize(temp_pdf_path) > 0:
                    convert_success = True
                    logger.info(f"Successfully converted DOCX to PDF using docx2pdf: {temp_pdf_path}")
                else:
                    logger.warning("docx2pdf conversion didn't produce a valid PDF")
            except ImportError:
                logger.warning("docx2pdf not installed. Cannot convert DOCX to PDF.")
            except Exception as dp_error:
                logger.warning(f"Error using docx2pdf for conversion: {str(dp_error)}")
        
        # If conversion to PDF was successful, use the PDF conversion function
        if convert_success and os.path.exists(temp_pdf_path):
            image_paths = convert_pdf_to_images(temp_pdf_path, output_dir)
            
        # If all conversion methods failed or we got no images, attempt direct rendering
        if not image_paths:
            logger.warning("PDF conversion methods failed. Falling back to direct DOCX rendering")
            
            try:
                import mammoth
                from PIL import Image, ImageDraw, ImageFont
                
                # Extract the HTML content from the DOCX
                with open(docx_path, "rb") as docx_file:
                    result = mammoth.convert_to_html(docx_file)
                    html = result.value
                    
                # Create an image with the text content
                # This is a very simplified approach - in production, you might want 
                # a more sophisticated HTML-to-image renderer
                
                # Split content into logical chunks for pages
                html_parts = html.split('<h1')
                if len(html_parts) == 1:  # No h1 tags, try paragraphs
                    html_parts = html.split('</p>')
                    
                # Limit number of "pages" to MAX_PAGES
                html_parts = html_parts[:MAX_PAGES]
                
                for i, part in enumerate(html_parts):
                    if not part.strip():
                        continue
                        
                    # Create a blank image
                    img = Image.new('RGB', (1240, 1754), color='white')  # A4 size at 150 DPI
                    d = ImageDraw.Draw(img)
                    
                    # Use default font
                    try:
                        font = ImageFont.truetype("Arial", 14)
                    except:
                        # Fallback to default
                        font = ImageFont.load_default()
                    
                    # Remove HTML tags for simplified text extraction
                    from html.parser import HTMLParser
                    
                    class MLStripper(HTMLParser):
                        def __init__(self):
                            super().__init__()
                            self.reset()
                            self.strict = False
                            self.convert_charrefs = True
                            self.text = []
                        def handle_data(self, d):
                            self.text.append(d)
                        def get_data(self):
                            return ''.join(self.text)
                    
                    stripper = MLStripper()
                    stripper.feed(part)
                    text = stripper.get_data()
                    
                    # Draw text on image
                    lines = []
                    line_height = 20
                    max_width = 1200
                    words = text.split()
                    
                    if words:
                        current_line = words[0]
                        for word in words[1:]:
                            # Check if adding this word exceeds image width
                            test_line = current_line + " " + word
                            test_width = d.textlength(test_line, font=font)
                            if test_width <= max_width:
                                current_line = test_line
                            else:
                                lines.append(current_line)
                                current_line = word
                        lines.append(current_line)
                    
                    # Draw text lines on image
                    y_position = 50
                    for line in lines:
                        d.text((50, y_position), line, fill='black', font=font)
                        y_position += line_height
                    
                    # Save the image
                    image_path = os.path.join(output_dir, f"docx_page_{i + 1:03d}.png")
                    img.save(image_path)
                    image_paths.append(image_path)
                    logger.info(f"Created image for DOCX content part {i + 1}: {image_path}")
                    
                    # Prevent creating too many images
                    if len(image_paths) >= MAX_PAGES:
                        break
                        
            except Exception as direct_error:
                logger.error(f"Error in direct DOCX rendering: {str(direct_error)}")
                
    except Exception as e:
        logger.error(f"Error in DOCX to image conversion: {str(e)}")
        
    finally:
        # Cleanup the temporary PDF file
        if os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
            except:
                pass
    
    return image_paths

def image_to_base64(image_path: str) -> str:
    """
    Convert an image file to a base64 string
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string with content type prefix
    """
    try:
        # Determine the MIME type based on file extension
        file_ext = os.path.splitext(image_path)[1].lower()
        
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        
        mime_type = mime_types.get(file_ext, 'image/png')
        
        with open(image_path, "rb") as img_file:
            base64_data = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{base64_data}"
            
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return ""

async def process_document_with_multimodal_api(
    file_path: str, 
    prompt: str, 
    system_message: str
) -> Dict[str, Any]:
    """
    Process a document file using multimodal API by converting it to images
    
    Args:
        file_path: Path to the document file
        prompt: Text prompt describing what to extract from the document
        system_message: System message for the AI
        
    Returns:
        API response dictionary
    """
    try:
        # Create temporary directory for images
        with tempfile.TemporaryDirectory(prefix="doc_images_") as temp_dir:
            # Convert document to images
            start_time = time.time()
            logger.info(f"Converting document to images: {file_path}")
            
            image_paths = convert_document_to_images(file_path, temp_dir)
            
            if not image_paths:
                logger.error(f"Failed to convert document to images: {file_path}")
                return {"error": "Failed to convert document to images"}
                
            logger.info(f"Generated {len(image_paths)} images in {time.time() - start_time:.2f} seconds")
            
            # Convert images to base64
            base64_images = []
            for img_path in image_paths:
                base64_str = image_to_base64(img_path)
                if base64_str:
                    base64_images.append(base64_str)
                    
            if not base64_images:
                logger.error("Failed to convert any images to base64")
                return {"error": "Failed to convert images to base64"}
                
            logger.info(f"Converted {len(base64_images)} images to base64")
            
            # Prepare messages for the API
            messages = [
                {
                    "role": "system",
                    "content": system_message
                }
            ]
            
            # Add each image with the prompt to user message
            content_items = [{"type": "text", "text": prompt}]
            
            # Add images (limit to first 10 to avoid token limits)
            max_images = min(10, len(base64_images))
            for i in range(max_images):
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": base64_images[i]
                    }
                })
                
            # Add image count info to the prompt
            if len(base64_images) > max_images:
                content_items.append({
                    "type": "text",
                    "text": f"Note: Only showing {max_images} out of {len(base64_images)} pages from this document due to token limits."
                })
                
            # Add user message with text and images
            messages.append({
                "role": "user",
                "content": content_items
            })
            
            # Call the OpenRouter API
            start_time = time.time()
            logger.info("Calling OpenRouter multimodal API")
            
            # Select a model that supports vision capabilities
            vision_model = "anthropic/claude-3-5-sonnet"
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": vision_model,
                    "messages": messages,
                    "temperature": 0.2,  # Lower temperature for more factual output
                    "max_tokens": 6000  # Increase max tokens for detailed analysis of more pages
                },
                timeout=180  # Longer timeout for processing more images
            )
            
            api_time = time.time() - start_time
            logger.info(f"OpenRouter API call completed in {api_time:.2f} seconds")
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code} - {response.text}"}
                
            # Parse response
            response_data = response.json()
            return response_data
            
    except Exception as e:
        logger.error(f"Error in multimodal document processing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}
        
async def extract_text_with_multimodal(file_path: str) -> str:
    """
    Extract text from a document using multimodal vision API
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text content
    """
    prompt = (
        "Please analyze this document and extract ALL the text content you can see. "
        "Include all text from headers, paragraphs, tables, forms, and any other visible text elements. "
        "Maintain the document's structure and formatting as much as possible. "
        "If there are multiple pages, process each page thoroughly. "
        "Do not summarize - provide the complete text content exactly as it appears in the document."
    )
    
    system_message = (
        "You are a document OCR assistant that extracts text content from document images. "
        "Your task is to extract ALL visible text from the documents, maintaining structure and formatting. "
        "Include all text from headers, tables, forms, and all visible elements. "
        "Be thorough and detail-oriented. Do not summarize or interpret - extract the exact text."
    )
    
    response = await process_document_with_multimodal_api(file_path, prompt, system_message)
    
    if "error" in response:
        return f"Error: {response['error']}"
        
    if (
        "choices" in response
        and len(response["choices"]) > 0
        and "message" in response["choices"][0]
        and "content" in response["choices"][0]["message"]
    ):
        extracted_text = response["choices"][0]["message"]["content"]
        logger.info(f"Successfully extracted {len(extracted_text)} characters with multimodal API")
        return extracted_text
    else:
        logger.error(f"Unexpected API response format: {json.dumps(response)}")
        return "Error: Unexpected API response format" 