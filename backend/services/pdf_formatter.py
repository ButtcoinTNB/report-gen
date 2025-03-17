from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
import os
import asyncio
import uuid
import io
import sys
import tempfile
import re
from typing import Dict, Any, List, Optional
from config import settings
from utils.error_handler import logger

# Conditionally import WeasyPrint and related modules
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint is available for PDF generation")
except ImportError as e:
    WEASYPRINT_AVAILABLE = False
    logger.warning(f"WeasyPrint is not available: {str(e)}")

# Conditionally import pdfrw
try:
    import pdfrw
    PDFRW_AVAILABLE = True
    logger.info("pdfrw is available for PDF manipulation")
except ImportError as e:
    PDFRW_AVAILABLE = False
    logger.warning(f"pdfrw is not available: {str(e)}")


def check_pdf_libraries():
    """
    Check if the required PDF libraries are available and compatible.
    Returns a dictionary with information about available libraries.
    """
    libraries = {
        "reportlab": True,  # Always available as it's a core dependency
        "weasyprint": WEASYPRINT_AVAILABLE,
        "pdfrw": PDFRW_AVAILABLE,
    }
    
    # Check specific versions if libraries are available
    if WEASYPRINT_AVAILABLE:
        import weasyprint
        libraries["weasyprint_version"] = weasyprint.__version__
        logger.info(f"WeasyPrint version: {weasyprint.__version__}")
    
    if PDFRW_AVAILABLE:
        import pdfrw
        libraries["pdfrw_version"] = pdfrw.__version__
        logger.info(f"pdfrw version: {pdfrw.__version__}")
    
    # Check compatibility between WeasyPrint and pdfrw
    # This is a known issue with certain versions
    if WEASYPRINT_AVAILABLE and PDFRW_AVAILABLE:
        try:
            # Create a minimal PDF using WeasyPrint
            html = HTML(string="<p>Test</p>")
            pdf_bytes = html.write_pdf()
            
            # Try to read it with pdfrw
            pdf_file = io.BytesIO(pdf_bytes)
            pdfrw.PdfReader(pdf_file)
            
            libraries["weasyprint_pdfrw_compatible"] = True
            logger.info("WeasyPrint and pdfrw are compatible")
        except Exception as e:
            libraries["weasyprint_pdfrw_compatible"] = False
            libraries["compatibility_error"] = str(e)
            logger.warning(f"WeasyPrint and pdfrw compatibility issue: {str(e)}")
    
    return libraries


def generate_weasyprint_pdf(report_text: str, output_path: str, reference_metadata: Dict[str, Any]) -> str:
    """
    Generate a PDF using WeasyPrint.
    """
    logger.info(f"Generating PDF with WeasyPrint: {output_path}")
    
    # Convert markdown-like formatting to HTML
    html_content = convert_markdown_to_html(report_text)
    
    # Extract headers and footers
    headers = reference_metadata.get("headers", [])
    footers = reference_metadata.get("footers", [])
    
    # Create a basic HTML template with styling
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Insurance Report</title>
        <style>
            @page {{
                margin: 2.5cm 2cm;
                @top-center {{
                    content: {headers[0] if headers else "'Insurance Report'"};
                    font-family: Helvetica, Arial, sans-serif;
                    font-weight: bold;
                    font-size: 10pt;
                }}
                @bottom-center {{
                    content: {footers[0].replace('{page}', 'counter(page)').replace('{total_pages}', 'counter(pages)') if footers else "'Page ' counter(page) ' of ' counter(pages)"};
                    font-family: Helvetica, Arial, sans-serif;
                    font-style: italic;
                    font-size: 8pt;
                    color: #555;
                }}
            }}
            body {{
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.4;
                color: #333;
            }}
            h1, h2, h3, h4, h5, h6 {{
                font-family: Helvetica, Arial, sans-serif;
                font-weight: bold;
                margin-top: 1em;
                margin-bottom: 0.5em;
                color: #000;
            }}
            h1 {{ font-size: 16pt; }}
            h2 {{ font-size: 14pt; }}
            h3 {{ font-size: 12pt; }}
            p {{ margin: 0.5em 0; }}
            ul, ol {{ margin: 0.5em 0; padding-left: 2em; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
            th, td {{ border: 1px solid #ddd; padding: 0.5em; text-align: left; }}
            th {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    try:
        # Configure fonts
        font_config = FontConfiguration()
        
        # Create HTML object
        html = HTML(string=html_template)
        
        # Generate PDF
        html.write_pdf(output_path, font_config=font_config)
        
        logger.info(f"Successfully generated PDF with WeasyPrint at {output_path}")
        
        # Return absolute path
        return os.path.abspath(output_path)
    except Exception as e:
        logger.error(f"Error generating PDF with WeasyPrint: {str(e)}")
        logger.exception("WeasyPrint PDF generation failed with exception")
        raise


def convert_markdown_to_html(markdown_text: str) -> str:
    """
    Convert basic markdown formatting to HTML.
    """
    html = markdown_text
    
    # Replace markdown headers with HTML headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    
    # Replace markdown bold with HTML bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Replace markdown italic with HTML italic
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # Replace markdown lists with HTML lists
    html = re.sub(r'^\- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    
    # Wrap paragraphs
    paragraphs = []
    current_paragraph = []
    in_list = False
    
    for line in html.split('\n'):
        if line.strip() == '':
            if current_paragraph:
                if in_list:
                    paragraphs.append('<ul>' + ''.join(current_paragraph) + '</ul>')
                    in_list = False
                else:
                    paragraphs.append('<p>' + ''.join(current_paragraph) + '</p>')
                current_paragraph = []
        elif line.startswith('<li>'):
            in_list = True
            current_paragraph.append(line)
        elif line.startswith('<h'):
            if current_paragraph:
                if in_list:
                    paragraphs.append('<ul>' + ''.join(current_paragraph) + '</ul>')
                    in_list = False
                else:
                    paragraphs.append('<p>' + ''.join(current_paragraph) + '</p>')
                current_paragraph = []
            paragraphs.append(line)
        else:
            if in_list and not line.startswith('<li>'):
                paragraphs.append('<ul>' + ''.join(current_paragraph) + '</ul>')
                current_paragraph = [line]
                in_list = False
            else:
                current_paragraph.append(line)
    
    if current_paragraph:
        if in_list:
            paragraphs.append('<ul>' + ''.join(current_paragraph) + '</ul>')
        else:
            paragraphs.append('<p>' + ''.join(current_paragraph) + '</p>')
    
    return ''.join(paragraphs)


def generate_pdf(
    report_text: str, output_filename: str, reference_metadata: Dict[str, Any]
) -> str:
    """
    Generate a PDF from report text, using reference metadata for formatting.
    
    Args:
        report_text: The text content of the report
        output_filename: Filename for the output PDF
        reference_metadata: Dictionary containing headers and footers
        
    Returns:
        The full path to the generated PDF
    """
    # Ensure directory exists
    os.makedirs(settings.GENERATED_REPORTS_DIR, exist_ok=True)
    
    # Create full path
    output_path = os.path.join(settings.GENERATED_REPORTS_DIR, output_filename)
    
    # Check for WeasyPrint availability first
    if WEASYPRINT_AVAILABLE:
        try:
            logger.info("Attempting to generate PDF with WeasyPrint")
            return generate_weasyprint_pdf(report_text, output_path, reference_metadata)
        except Exception as e:
            logger.warning(f"WeasyPrint failed, falling back to ReportLab: {str(e)}")
            # Fall back to ReportLab
    
    logger.info("Generating PDF with ReportLab")
    
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        # Define styles
        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            textColor=colors.darkgrey
        )

        # Add headers
        if "headers" in reference_metadata and reference_metadata["headers"]:
            y_offset = 40
            for i, header in enumerate(reference_metadata["headers"]):
                c.setFont("Helvetica-Bold", 12)
                # Center the header text
                header_width = c.stringWidth(header, "Helvetica-Bold", 12)
                x_position = (width - header_width) / 2
                c.drawString(x_position, height - y_offset, header)
                y_offset += 20

        # For calculating text positions
        top_margin = 100  # Start text 100pts from top
        bottom_margin = 50  # Stop 50pts from bottom
        y_position = height - top_margin

        # Split report text by sections (if using markdown-style headers)
        sections = report_text.split('\n# ')
        
        # Process first part (non-header text if any)
        intro_text = sections[0]
        remaining_sections = []
        
        if len(sections) > 1:
            # Process each section (adding back the # that was removed in the split)
            for i in range(1, len(sections)):
                remaining_sections.append("# " + sections[i])
        
        # Process introduction text
        intro_lines = simpleSplit(intro_text, "Helvetica", 11, width - 100)
        
        c.setFont("Helvetica", 11)
        for line in intro_lines:
            if y_position < bottom_margin:  # Start a new page if needed
                c.showPage()
                y_position = height - top_margin
                c.setFont("Helvetica", 11)
                
                # Add headers to new page
                if "headers" in reference_metadata and reference_metadata["headers"]:
                    y_offset = 40
                    for i, header in enumerate(reference_metadata["headers"]):
                        c.setFont("Helvetica-Bold", 12)
                        header_width = c.stringWidth(header, "Helvetica-Bold", 12)
                        x_position = (width - header_width) / 2
                        c.drawString(x_position, height - y_offset, header)
                        y_offset += 20
                    c.setFont("Helvetica", 11)  # Reset font

            c.drawString(50, y_position, line)
            y_position -= 15  # Smaller line spacing for normal text
        
        # Process remaining sections
        for section in remaining_sections:
            # Extract section title (everything before first newline)
            parts = section.split('\n', 1)
            section_title = parts[0].replace('# ', '').strip()
            section_content = parts[1] if len(parts) > 1 else ""
            
            # Add section title
            if y_position < bottom_margin + 30:  # Need more space for section title
                c.showPage()
                y_position = height - top_margin
                
                # Add headers to new page
                if "headers" in reference_metadata and reference_metadata["headers"]:
                    y_offset = 40
                    for i, header in enumerate(reference_metadata["headers"]):
                        c.setFont("Helvetica-Bold", 12)
                        header_width = c.stringWidth(header, "Helvetica-Bold", 12)
                        x_position = (width - header_width) / 2
                        c.drawString(x_position, height - y_offset, header)
                        y_offset += 20
            
            # Draw section title
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_position, section_title)
            y_position -= 20  # More space after section title
            
            # Draw section content
            c.setFont("Helvetica", 11)
            content_lines = simpleSplit(section_content, "Helvetica", 11, width - 100)
            
            for line in content_lines:
                if y_position < bottom_margin:  # Start a new page if needed
                    c.showPage()
                    y_position = height - top_margin
                    
                    # Add headers to new page
                    if "headers" in reference_metadata and reference_metadata["headers"]:
                        y_offset = 40
                        for i, header in enumerate(reference_metadata["headers"]):
                            c.setFont("Helvetica-Bold", 12)
                            header_width = c.stringWidth(header, "Helvetica-Bold", 12)
                            x_position = (width - header_width) / 2
                            c.drawString(x_position, height - y_offset, header)
                            y_offset += 20
                    c.setFont("Helvetica", 11)  # Reset font
                
                c.drawString(50, y_position, line)
                y_position -= 15

        # Add footers to all pages
        c.showPage()  # Finalize the current page
        
        # Get total number of pages
        total_pages = c.getPageNumber()
        
        # Go through each page and add footers
        for page_num in range(1, total_pages + 1):
            c.setFont("Helvetica-Oblique", 8)
            
            # Go to the page
            c.getPage(page_num - 1)
            
            if "footers" in reference_metadata and reference_metadata["footers"]:
                y_offset = 30
                for i, footer in enumerate(reference_metadata["footers"]):
                    # Replace {page} placeholder with actual page number
                    footer_text = footer.replace("{page}", str(page_num))
                    footer_text = footer_text.replace("{total_pages}", str(total_pages))
                    
                    # Center the footer
                    footer_width = c.stringWidth(footer_text, "Helvetica-Oblique", 8)
                    x_position = (width - footer_width) / 2
                    
                    c.drawString(x_position, y_offset, footer_text)
                    y_offset += 15
        
        c.save()
        logger.info(f"Successfully generated PDF with ReportLab at {output_path}")
        
        # Return absolute path
        return os.path.abspath(output_path)
    except Exception as e:
        logger.error(f"Error generating PDF with ReportLab: {str(e)}")
        logger.exception("PDF generation failed with exception")
        raise


async def format_report_as_pdf(
    report_content, reference_metadata, is_preview=False, filename=None
):
    """
    Async wrapper for generate_pdf to match the expected function signature in format.py
    
    Args:
        report_content: The content of the report
        reference_metadata: Dictionary containing headers and footers
        is_preview: Whether this is a preview or final version
        filename: Optional filename for the output PDF
        
    Returns:
        The full path to the generated PDF
    """
    if filename is None:
        unique_id = str(uuid.uuid4())[:8]
        filename = f"preview_{unique_id}.pdf" if is_preview else f"report_{unique_id}.pdf"

    try:
        # Check PDF libraries compatibility
        libraries = check_pdf_libraries()
        logger.info(f"PDF library compatibility check: {libraries}")
        
        # Log when starting PDF generation
        logger.info(f"Starting PDF generation for {'preview' if is_preview else 'final'} mode")
        logger.info(f"Output filename: {filename}")
        
        # Run the synchronous function in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, generate_pdf, report_content, filename, reference_metadata
        )
        
        # Log successful PDF generation
        logger.info(f"PDF generation completed: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Error in format_report_as_pdf: {str(e)}")
        logger.exception("PDF formatting failed with exception")
        raise
