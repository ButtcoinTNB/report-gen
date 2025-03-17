# This is a corrected version of the pdf_formatter.py file
# Focusing on the part with the indentation error

import os
import io
import re
import time
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.platypus.flowables import KeepTogether
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

# This is the function with the indentation error
async def format_report_as_pdf(report_text, reference_metadata=None, is_preview=False, filename=None):
    """
    Format the report as a PDF and save to disk
    
    Args:
        report_text (str): The markdown text to format
        reference_metadata (dict): Optional metadata from reference PDFs
        is_preview (bool): Whether this is a preview or final version
        filename (str): Optional filename to use
        
    Returns:
        str: Path to the generated PDF
    """
    try:
        # Create a consistent directory structure for generated reports
        from config import settings
        reports_dir = settings.GENERATED_REPORTS_DIR
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate a unique filename if not provided
        if not filename:
            timestamp = int(time.time())
            filename = f"report_{timestamp}.pdf"
            
        output_path = os.path.join(reports_dir, filename)
        logger.info(f"Creating PDF at {output_path}")
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )
        
        # Initialize story (list of flowables)
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Add custom styles
        heading1_style = ParagraphStyle(
            name='Heading1',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=24,
            textColor=colors.darkblue
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
                for paragraph in section_content.split('\n\n'):
                    if paragraph.strip():
                        story.append(Paragraph(paragraph, normal_style))
        
        # Build the PDF
        doc.build(story)
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise 