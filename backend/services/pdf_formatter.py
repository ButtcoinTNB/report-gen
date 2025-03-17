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
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import tempfile
import re
from typing import Dict, Any, List, Optional
from config import settings


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
        print(f"Successfully generated PDF at {output_path}")
        
        # Return absolute path
        return os.path.abspath(output_path)
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
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
        # Run the synchronous function in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, generate_pdf, report_content, filename, reference_metadata
        )
    except Exception as e:
        print(f"Error in format_report_as_pdf: {str(e)}")
        raise
