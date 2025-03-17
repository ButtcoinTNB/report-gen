from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import os
import asyncio
import uuid
import re


def parse_markdown(doc, markdown_text):
    """
    Parse markdown text and add it to the document with proper formatting.
    
    Args:
        doc: The Document object
        markdown_text: Text with markdown formatting
    """
    # Split text into paragraphs
    paragraphs = markdown_text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue  # Skip empty paragraphs
        
        # Check for headers (# Header)
        header_match = re.match(r'^(#{1,6})\s+(.+)$', paragraph)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2).strip()
            doc.add_heading(text, level)
            continue
        
        # Check for unordered list items (- item or * item)
        list_match = re.match(r'^\s*[-*]\s+(.+)$', paragraph)
        if list_match:
            item_text = list_match.group(1)
            p = doc.add_paragraph(style='List Bullet')
            process_inline_formatting(p, item_text)
            continue
        
        # Check for ordered list items (1. item)
        ordered_list_match = re.match(r'^\s*(\d+)\.\s+(.+)$', paragraph)
        if ordered_list_match:
            item_text = ordered_list_match.group(2)
            p = doc.add_paragraph(style='List Number')
            process_inline_formatting(p, item_text)
            continue
        
        # Regular paragraph
        p = doc.add_paragraph()
        process_inline_formatting(p, paragraph)


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


def generate_docx(report_text, output_filename, reference_metadata=None):
    """
    Creates a DOCX with AI-generated report text, inserting it into a template.
    
    Args:
        report_text: The content of the report
        output_filename: The filename for the output DOCX
        reference_metadata: Dictionary containing format information (optional)
        
    Returns:
        The full path to the generated DOCX
    """
    # Ensure directory exists
    os.makedirs("generated_reports", exist_ok=True)
    
    # Create full path
    output_path = os.path.join("generated_reports", output_filename)
    
    try:
        # Check if a template exists
        template_path = os.path.join("backend", "reference_reports", "template.docx")
        
        if os.path.exists(template_path):
            # Use the template if it exists
            doc = Document(template_path)
            
            # Clear existing content while preserving styles and structure
            # Remove all paragraphs except the first one (to maintain document properties)
            if len(doc.paragraphs) > 0:
                # Keep track of the first paragraph to preserve document properties
                first_para = doc.paragraphs[0]
                
                # Remove all content from all paragraphs
                for i in range(len(doc.paragraphs)):
                    if i < len(doc.paragraphs):  # Check again as length may change
                        # Clear text but keep the paragraph
                        p = doc.paragraphs[i]
                        p.clear()
                
                # Also clear all tables
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                paragraph.clear()
        else:
            # Create a new document if no template exists
            doc = Document()
            # Add a title
            doc.add_heading('Report', 0)
        
        # Parse markdown formatting in the report text
        parse_markdown(doc, report_text)
        
        # Save the document
        doc.save(output_path)
        
        return output_path
    except Exception as e:
        print(f"Error generating DOCX: {e}")
        raise e


async def format_report_as_docx(report_content, reference_metadata=None, filename=None):
    """
    Formats the report content as a DOCX document.
    
    Args:
        report_content: The text content of the report
        reference_metadata: Dictionary containing format information (optional)
        filename: Custom filename (optional)
        
    Returns:
        Dictionary with the path to the generated DOCX
    """
    if not filename:
        filename = f"report_{uuid.uuid4().hex}.docx"
    
    # Generate the DOCX
    docx_path = generate_docx(report_content, filename, reference_metadata)
    
    return {
        "docx_path": docx_path,
        "filename": filename
    } 