from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
import os
import asyncio
import uuid
import io
import sys
import tempfile
import re
from typing import Dict, Any, List, Optional, Tuple
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


def check_pdf_libraries() -> Dict[str, Any]:
    """
    Check if required PDF libraries are available and test their compatibility.
    Returns a dictionary with library availability and compatibility results.
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
    
    # Full compatibility test between WeasyPrint and pdfrw
    if WEASYPRINT_AVAILABLE and PDFRW_AVAILABLE:
        try:
            # Create minimal PDF using WeasyPrint
            html = HTML(string="<p>Test PDF</p>")
            pdf_bytes = html.write_pdf()
            
            # Load with pdfrw
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = pdfrw.PdfReader(pdf_file)
            
            # Modify the document
            pdf_writer = pdfrw.PdfWriter()
            for page in pdf_reader.pages:
                if hasattr(page, "/Title"):
                    page["/Title"] = pdfrw.objects.pdfstring.PdfString("Modified Title")
                pdf_writer.addpage(page)
            
            # Write modified PDF
            temp_pdf = io.BytesIO()
            pdf_writer.write(temp_pdf)
            
            # Validate new PDF
            temp_pdf.seek(0)
            pdfrw.PdfReader(temp_pdf)
            
            libraries["weasyprint_pdfrw_compatible"] = True
            logger.info("WeasyPrint and pdfrw are fully compatible - modification test passed")
        except Exception as e:
            libraries["weasyprint_pdfrw_compatible"] = False
            libraries["compatibility_error"] = str(e)
            logger.warning(f"WeasyPrint and pdfrw compatibility issue: {str(e)}")
    
    return libraries


def generate_weasyprint_pdf(report_text: str, output_path: str, reference_metadata: Dict[str, Any]) -> str:
    """
    Generate a PDF using WeasyPrint.
    
    Args:
        report_text: The text content to convert to PDF
        output_path: Path where the PDF will be saved
        reference_metadata: Dictionary containing headers, footers, etc.
        
    Returns:
        Absolute path to the generated PDF
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
    
    Args:
        markdown_text: Text with markdown-style formatting
        
    Returns:
        HTML-formatted text
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


class HeaderFooterCanvas(canvas.Canvas):
    """
    Custom canvas class for ReportLab that adds headers and footers to each page
    """
    
    def __init__(self, *args, **kwargs):
        self.headers = kwargs.pop('headers', [])
        self.footers = kwargs.pop('footers', [])
        self.width, self.height = A4
        self.page_count = 0
        canvas.Canvas.__init__(self, *args, **kwargs)
    
    def showPage(self):
        self.page_count += 1
        
        # Add headers
        if self.headers:
            self.saveState()
            self.setFont("Helvetica-Bold", 12)
            
            y_offset = self.height - 40
            for header in self.headers:
                # Center the header
                header_width = self.stringWidth(header, "Helvetica-Bold", 12)
                x_position = (self.width - header_width) / 2
                self.drawString(x_position, y_offset, header)
                y_offset -= 20
                
            self.restoreState()
        
        # Add footers
        if self.footers:
            self.saveState()
            self.setFont("Helvetica-Oblique", 8)
            
            y_offset = 30
            for footer in self.footers:
                # Replace placeholders with actual page numbers
                footer_text = footer.replace("{page}", str(self.page_count))
                # We don't know total pages yet, will be updated in save()
                footer_text = footer_text.replace("{total_pages}", "{total_pages}")
                
                # Center the footer
                footer_width = self.stringWidth(footer_text, "Helvetica-Oblique", 8)
                x_position = (self.width - footer_width) / 2
                self.drawString(x_position, y_offset, footer_text)
                y_offset += 15
                
            self.restoreState()
            
        canvas.Canvas.showPage(self)
        
    def save(self):
        # Process all pages to update the {total_pages} placeholder
        total_pages = self.page_count
        
        # We need to pass through each page and update footers if they contain {total_pages}
        for page_num in range(1, total_pages + 1):
            # Get page
            page = self._pageBuffer[page_num - 1]
            
            # Replace {total_pages} placeholder with the actual total
            updated_page = page.replace(b"{total_pages}", str(total_pages).encode())
            
            # Update page in buffer
            self._pageBuffer[page_num - 1] = updated_page
            
        canvas.Canvas.save(self)


def generate_reportlab_pdf(report_text: str, output_path: str, reference_metadata: Dict[str, Any]) -> str:
    """
    Generate a PDF using ReportLab's Platypus for proper text flow handling.
    
    Args:
        report_text: The text content to convert to PDF
        output_path: Path where the PDF will be saved
        reference_metadata: Dictionary containing headers, footers, etc.
        
    Returns:
        Absolute path to the generated PDF
    """
    logger.info(f"Generating PDF with ReportLab Platypus: {output_path}")
    
    # Extract headers and footers
    headers = reference_metadata.get("headers", [])
    footers = reference_metadata.get("footers", ["Page {page} of {total_pages}"])
    
    try:
        # Create a document template with custom canvas for headers/footers
        def make_canvas(*args, **kwargs):
            return HeaderFooterCanvas(
                *args, headers=headers, footers=footers, **kwargs
            )
        
        # Create the document template
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=70,  # Extra space for headers
            bottomMargin=40  # Extra space for footers
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'TitleStyle', 
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=16
        )
        
        heading1_style = ParagraphStyle(
            'Heading1Style', 
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=10
        )
        
        heading2_style = ParagraphStyle(
            'Heading2Style', 
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=8
        )
        
        normal_style = styles["Normal"]
        normal_style.spaceAfter = 10
        
        # Parse markdown and convert to Platypus elements
        sections = report_text.split('\n# ')
        
        # Process first part (introduction)
        intro_text = sections[0].strip()
        if intro_text:
            for paragraph in intro_text.split('\n\n'):
                if paragraph.strip():
                    story.append(Paragraph(paragraph, normal_style))
        
        # Process sections with headers
            for i in range(1, len(sections)):
            section = sections[i]
            section_parts = section.split('\n', 1)
            
            # Add section title
            section_title = section_parts[0].strip()
            story.append(Paragraph(section_title, heading1_style))
            
            # Process section content if any
            if len(section_parts) > 1:
                section_content = section_parts[1].strip()
                
                # Process subsections if they exist
                subsections = section_content.split('\n## ')
                
                # Process first part (before any subsection)
                main_content = subsections[0].strip()
                if main_content:
                    for paragraph in main_content.split('\n\n'):
                        if paragraph.strip():
                            story.append(Paragraph(paragraph, normal_style))
                
                # Process each subsection
                for j in range(1, len(subsections)):
                    subsection = subsections[j]
                    subsection_parts = subsection.split('\n', 1)
                    
                    # Add subsection title
                    subsection_title = subsection_parts[0].strip()
                    story.append(Paragraph(subsection_title, heading2_style))
                    
                    # Process subsection content if any
                    if len(subsection_parts) > 1:
                        subsection_content = subsection_parts[1].strip()
                        if subsection_content:
                            for paragraph in subsection_content.split('\n\n'):
                                if paragraph.strip():
                                    story.append(Paragraph(paragraph, normal_style))
        
        # Build the document
        doc.build(story, canvasmaker=make_canvas)
        
        logger.info(f"Successfully generated PDF with ReportLab at {output_path}")
        
        # Return absolute path
        return os.path.abspath(output_path)
    except Exception as e:
        logger.error(f"Error generating PDF with ReportLab Platypus: {str(e)}")
        logger.exception("ReportLab PDF generation failed with exception")
        raise


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
    
    # Try WeasyPrint first (if available)
    if WEASYPRINT_AVAILABLE:
        try:
            logger.info("Attempting to generate PDF with WeasyPrint")
            return generate_weasyprint_pdf(report_text, output_path, reference_metadata)
        except Exception as weasy_err:
            logger.warning(f"WeasyPrint failed, falling back to ReportLab: {str(weasy_err)}")
    else:
        logger.info("WeasyPrint is not available, using ReportLab")
    
    # If WeasyPrint is not available or failed, use ReportLab
    try:
        return generate_reportlab_pdf(report_text, output_path, reference_metadata)
    except Exception as reportlab_err:
        logger.error(f"ReportLab also failed: {str(reportlab_err)}")
        logger.exception("All PDF generation methods failed")
        raise RuntimeError("Failed to generate PDF: Both WeasyPrint and ReportLab methods failed.") from reportlab_err


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
