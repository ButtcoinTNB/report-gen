#!/usr/bin/env python
"""
Diagnostic script for the Insurance Report Generator
This script checks system configuration, dependencies, and runs tests to ensure all components
are working correctly.
"""

import os
import sys
import asyncio
import logging
import importlib.util
from pathlib import Path

# Setup base logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("diagnostics")

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    from utils import error_handler
    from services import pdf_formatter, pdf_extractor, ai_service
except ImportError as e:
    logger.critical(f"Failed to import a required module: {e}")
    sys.exit(1)

def check_environment():
    """Check environment variables and configuration"""
    logger.info("=== Environment Check ===")
    
    required_vars = [
        "OPENROUTER_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "UPLOAD_DIR",
        "GENERATED_REPORTS_DIR"
    ]
    
    for var in required_vars:
        if hasattr(settings, var):
            value = getattr(settings, var)
            masked_value = value[:5] + "..." + value[-5:] if value and len(value) > 10 else "<empty>"
            logger.info(f"✅ {var} is set to {masked_value}")
        else:
            logger.error(f"❌ {var} is not set in config")
    
    # Check directories
    dirs_to_check = [
        settings.UPLOAD_DIR,
        settings.GENERATED_REPORTS_DIR
    ]
    
    for dir_path in dirs_to_check:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"✅ Created directory {dir_path}")
            except Exception as e:
                logger.error(f"❌ Failed to create directory {dir_path}: {e}")
        else:
            logger.info(f"✅ Directory exists: {dir_path}")
    
    return True


def check_dependencies():
    """Check if all required dependencies are installed"""
    logger.info("=== Dependency Check ===")
    
    packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "reportlab",
        "weasyprint",
        "pdfrw",
        "python-docx",
        "httpx",
        "pymupdf",
        "supabase",
    ]
    
    all_found = True
    
    for package in packages:
        spec = importlib.util.find_spec(package)
        if spec is not None:
            logger.info(f"✅ {package} is installed")
        else:
            logger.error(f"❌ {package} is not installed")
            all_found = False
    
    return all_found


async def test_openrouter_api():
    """Test OpenRouter API connection"""
    logger.info("=== OpenRouter API Test ===")
    
    if not hasattr(settings, "OPENROUTER_API_KEY") or not settings.OPENROUTER_API_KEY:
        logger.error("❌ OpenRouter API key is not set")
        return False
    
    try:
        # Create a simple test message for the API
        messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Respond with 'API test successful' to confirm this test."}
        ]
        
        # Use our new function with retry logic
        result = await ai_service.call_openrouter_api(messages, max_retries=1)
        
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            response_text = result["choices"][0]["message"]["content"]
            logger.info(f"✅ OpenRouter API test successful: {response_text[:50]}...")
            return True
        else:
            logger.error(f"❌ OpenRouter API returned unexpected format: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ OpenRouter API test failed: {e}")
        return False


def test_pdf_extraction():
    """Test PDF extraction functionality"""
    logger.info("=== PDF Extraction Test ===")
    
    # Create a test PDF file
    test_pdf_path = os.path.join(settings.GENERATED_REPORTS_DIR, "test_pdf_extraction.pdf")
    
    try:
        # Generate a simple PDF for testing
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        c.drawString(100, 750, "PDF Extraction Test")
        c.drawString(100, 700, "This is a test PDF file.")
        c.save()
        
        logger.info(f"✅ Created test PDF at {test_pdf_path}")
        
        # Extract text from the PDF
        extracted_text = pdf_extractor.extract_text_from_pdf(test_pdf_path)
        
        if "PDF Extraction Test" in extracted_text and "This is a test PDF file" in extracted_text:
            logger.info(f"✅ PDF extraction successful: {extracted_text[:50]}...")
            return True
        else:
            logger.error(f"❌ PDF extraction failed to extract expected text: {extracted_text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ PDF extraction test failed: {e}")
        return False
    finally:
        # Clean up the test file
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)


def test_pdf_generation():
    """Test PDF generation functionality"""
    logger.info("=== PDF Generation Test ===")
    
    test_output_path = os.path.join(settings.GENERATED_REPORTS_DIR, "test_generation.pdf")
    
    try:
        # Simple test content
        test_content = "# Test Report\n\nThis is a test report for PDF generation.\n\n## Section 1\n\nTest content for section 1."
        
        # Reference metadata
        ref_metadata = {
            "headers": ["TEST REPORT"],
            "footers": ["Page {page} of {total_pages}"]
        }
        
        # Test PDF generation
        output_path = pdf_formatter.generate_pdf(test_content, "test_generation.pdf", ref_metadata)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"✅ PDF generation successful: {output_path} ({os.path.getsize(output_path)} bytes)")
            
            # Check compatibility between Weasyprint and pdfrw if both are available
            pdf_libs = pdf_formatter.check_pdf_libraries()
            if pdf_libs.get("weasyprint") and pdf_libs.get("pdfrw"):
                if pdf_libs.get("weasyprint_pdfrw_compatible", False):
                    logger.info("✅ WeasyPrint and pdfrw are compatible")
                else:
                    logger.warning(f"⚠️ WeasyPrint and pdfrw compatibility issue: {pdf_libs.get('compatibility_error', 'Unknown error')}")
            
            return True
        else:
            logger.error(f"❌ PDF generation failed: {output_path} does not exist or is empty")
            return False
            
    except Exception as e:
        logger.error(f"❌ PDF generation test failed: {e}")
        return False
    finally:
        # Clean up the test file
        if os.path.exists(test_output_path):
            os.remove(test_output_path)


def test_error_handler():
    """Test the error handler functionality"""
    logger.info("=== Error Handler Test ===")
    
    try:
        # Test basic exception handling
        try:
            raise ValueError("Test error")
        except Exception as e:
            error_response = error_handler.handle_exception(e, "test operation", include_traceback=True)
            logger.error("This line should not be reached")
            return False
    except Exception as e:
        if "ValueError" in str(e) and "Test error" in str(e) and "test operation" in str(e):
            logger.info("✅ Error handler correctly processes exceptions")
            return True
        else:
            logger.error(f"❌ Error handler failed to properly format exception: {e}")
            return False


async def run_diagnostics():
    """Run all diagnostic checks"""
    logger.info("Starting insurance-report-generator diagnostics...")
    
    # Run all the checks
    env_check = check_environment()
    dep_check = check_dependencies()
    error_check = test_error_handler()
    pdf_extraction_check = test_pdf_extraction()
    pdf_generation_check = test_pdf_generation()
    api_check = await test_openrouter_api()
    
    # Print summary
    logger.info("\n=== Diagnostic Summary ===")
    logger.info(f"Environment check: {'✅ PASSED' if env_check else '❌ FAILED'}")
    logger.info(f"Dependency check: {'✅ PASSED' if dep_check else '❌ FAILED'}")
    logger.info(f"Error handler check: {'✅ PASSED' if error_check else '❌ FAILED'}")
    logger.info(f"PDF extraction check: {'✅ PASSED' if pdf_extraction_check else '❌ FAILED'}")
    logger.info(f"PDF generation check: {'✅ PASSED' if pdf_generation_check else '❌ FAILED'}")
    logger.info(f"OpenRouter API check: {'✅ PASSED' if api_check else '❌ FAILED'}")
    
    total_passed = sum([env_check, dep_check, error_check, pdf_extraction_check, pdf_generation_check, api_check])
    logger.info(f"\nOverall result: {total_passed}/6 checks passed")
    
    if total_passed == 6:
        logger.info("✅ All diagnostic checks passed!")
        return True
    else:
        logger.warning("⚠️ Some diagnostic checks failed. See the logs above for details.")
        return False


if __name__ == "__main__":
    try:
        # Create diagnostic directory if it doesn't exist
        os.makedirs("backend/logs", exist_ok=True)
        
        # Add file handler to log to a file
        file_handler = logging.FileHandler("backend/logs/diagnostic.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        # Run diagnostics
        asyncio.run(run_diagnostics())
    except Exception as e:
        logger.critical(f"Diagnostic script encountered an unhandled exception: {e}", exc_info=True)
        sys.exit(1) 