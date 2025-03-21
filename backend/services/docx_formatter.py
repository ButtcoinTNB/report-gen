from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_ALIGN_PARAGRAPH
import os
import asyncio
import uuid
import re
from config import settings
from pathlib import Path
from typing import Dict, Any, Optional
from backend.utils.error_handler import handle_exception, logger
from .docx_service import docx_service


def parse_markdown(doc: Document, markdown_text: str) -> None:
    """
    Parse markdown text and add it to the document with proper formatting.
    
    Args:
        doc: Document to add content to
        markdown_text: Markdown text to parse
    """
    try:
        # Split text into paragraphs
        paragraphs = markdown_text.split('\n\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # Handle headings
            if paragraph.startswith('#'):
                level = len(re.match('^#+', paragraph).group())
                text = paragraph.lstrip('#').strip()
                doc.add_heading(text, level=level)
                continue
            
            # Handle lists
            if paragraph.strip().startswith('- '):
                items = paragraph.strip().split('\n')
                for item in items:
                    if item.strip().startswith('- '):
                        p = doc.add_paragraph()
                        p.style = 'List Bullet'
                        p.add_run(item.strip('- '))
                continue
            
            # Regular paragraph
            p = doc.add_paragraph()
            p.add_run(paragraph.strip())
            
    except Exception as e:
        handle_exception(e, "Markdown parsing")
        raise


def process_inline_formatting(paragraph, text):
    """
    Process inline markdown formatting (bold, italic, etc.)
    
    Args:
        paragraph: The paragraph object to add text to
        text: Text with inline markdown formatting
    """
    # Process bold and italic formatting
    parts = []
    current_pos = 0
    
    # Find all bold and italic patterns
    # Bold: **text**
    # Italic: *text*
    # Bold+Italic: ***text***
    pattern = r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)'
    
    for match in re.finditer(pattern, text):
        # Add text before the match
        if match.start() > current_pos:
            parts.append((text[current_pos:match.start()], False, False))
        
        # Process the match
        match_text = match.group(0)
        if match_text.startswith('***') and match_text.endswith('***'):
            # Bold and italic
            content = match_text[3:-3]
            parts.append((content, True, True))
        elif match_text.startswith('**') and match_text.endswith('**'):
            # Bold
            content = match_text[2:-2]
            parts.append((content, True, False))
        elif match_text.startswith('*') and match_text.endswith('*'):
            # Italic
            content = match_text[1:-1]
            parts.append((content, False, True))
        
        current_pos = match.end()
    
    # Add any remaining text
    if current_pos < len(text):
        parts.append((text[current_pos:], False, False))
    
    # Add all parts to the paragraph with appropriate formatting
    for part_text, bold, italic in parts:
        run = paragraph.add_run(part_text)
        run.bold = bold
        run.italic = italic


def replace_template_variables(doc: Document, variables: Dict[str, Any]) -> None:
    """
    Replace all {{ variable }} placeholders in the document with their values.
    
    Args:
        doc: Document to process
        variables: Dictionary of variable names and values
    """
    try:
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                text = run.text
                for var_name, var_value in variables.items():
                    placeholder = f"{{{{ {var_name} }}}}"
                    if placeholder in text:
                        text = text.replace(placeholder, str(var_value))
                run.text = text
                
        # Also check tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            text = run.text
                            for var_name, var_value in variables.items():
                                placeholder = f"{{{{ {var_name} }}}}"
                                if placeholder in text:
                                    text = text.replace(placeholder, str(var_value))
                            run.text = text
                            
    except Exception as e:
        handle_exception(e, "Template variable replacement")
        raise


def generate_docx(report_text: str, output_filename: str, reference_metadata: Optional[Dict[str, Any]] = None, template_variables: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a DOCX file using the template, replacing variables and appending report text.
    
    Args:
        report_text: Text content to append to the document
        output_filename: Name of the output file
        reference_metadata: Optional metadata from reference reports
        template_variables: Optional variables to replace in the template
        
    Returns:
        Path to the generated file
    """
    try:
        # Use docx_service to handle template and variable replacement
        if template_variables:
            report_id = docx_service.generate_report(template_variables)
            doc_path = docx_service.get_report_path(report_id)
        else:
            # Create a new document if no template variables
            doc = Document()
            
            # Add title
            title = doc.add_heading('Report', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add report text
            parse_markdown(doc, report_text)
            
            # Save the document
            doc_path = Path(output_filename)
            doc.save(str(doc_path))
        
        return str(doc_path)
        
    except Exception as e:
        handle_exception(e, "DOCX generation")
        raise


def format_report_as_docx(report_content: str, reference_metadata: Optional[Dict[str, Any]] = None, filename: Optional[str] = None, template_variables: Optional[Dict[str, Any]] = None) -> str:
    """
    Format the report content as a DOCX document.
    
    Args:
        report_content: Content to include in the report
        reference_metadata: Optional metadata from reference reports
        filename: Optional name for the output file
        template_variables: Optional variables to replace in the template
        
    Returns:
        Path to the generated file
    """
    try:
        if not filename:
            # Generate a unique filename
            from uuid import uuid4
            filename = f"report_{uuid4()}.docx"
        
        # Generate the DOCX file
        doc_path = generate_docx(
            report_content,
            filename,
            reference_metadata,
            template_variables
        )
        
        return doc_path
        
    except Exception as e:
        handle_exception(e, "Report formatting")
        raise 