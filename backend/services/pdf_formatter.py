# This is a corrected version of the pdf_formatter.py file
# Focusing on the part with the indentation error

import logging
import os
import time

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from utils.file_utils import safe_path_join

logger = logging.getLogger(__name__)


# This is the function with the indentation error
async def format_report_as_pdf(
    report_text, reference_metadata=None, is_preview=False, filename=None
):
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

        output_path = safe_path_join(reports_dir, filename)
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
            name="Heading1",
            parent=styles["Heading1"],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=24,
            textColor=colors.darkblue,
        )

        # Add error styles for better visibility of error messages
        error_title_style = ParagraphStyle(
            name="ErrorTitle",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=24,
            textColor=colors.red,
            alignment=TA_CENTER,
        )

        error_heading_style = ParagraphStyle(
            name="ErrorHeading",
            parent=styles["Heading2"],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.darkred,
        )

        error_text_style = ParagraphStyle(
            name="ErrorText",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=10,
            textColor=colors.black,
        )

        normal_style = styles["Normal"]
        normal_style.spaceAfter = 10

        # Check if this is an error report
        is_error_report = "ERROR: COULD NOT RETRIEVE REPORT CONTENT" in report_text

        # Parse markdown and convert to Platypus elements
        sections = report_text.split("\n# ")

        # Process first part (introduction)
        intro_text = sections[0].strip()
        if intro_text:
            for paragraph in intro_text.split("\n\n"):
                if paragraph.strip():
                    story.append(Paragraph(paragraph, normal_style))

        # Process sections with headers
        for i in range(1, len(sections)):
            section = sections[i]
            section_parts = section.split("\n", 1)

            # Add section title
            section_title = section_parts[0].strip()

            # Use error styling for error reports
            if is_error_report and i == 1:  # First section title in error report
                story.append(Paragraph(section_title, error_title_style))
                # Add a visible horizontal line
                story.append(Spacer(1, 0.1 * inch))
            else:
                story.append(Paragraph(section_title, heading1_style))

            # Process section content if any
            if len(section_parts) > 1:
                section_content = section_parts[1].strip()

                # Handle subsections (## headings)
                if "## " in section_content and is_error_report:
                    subsections = section_content.split("\n## ")

                    # Process first part if any
                    if subsections[0] and not subsections[0].startswith("## "):
                        for paragraph in subsections[0].split("\n\n"):
                            if paragraph.strip():
                                story.append(
                                    Paragraph(
                                        paragraph,
                                        (
                                            error_text_style
                                            if is_error_report
                                            else normal_style
                                        ),
                                    )
                                )

                    # Process subsections
                    for j in range(
                        1 if subsections[0].strip() else 0, len(subsections)
                    ):
                        subsection = subsections[j]
                        subsection_parts = subsection.split("\n", 1)

                        # Add subsection title
                        subsection_title = subsection_parts[0].strip()
                        story.append(
                            Paragraph(
                                subsection_title,
                                (
                                    error_heading_style
                                    if is_error_report
                                    else styles["Heading2"]
                                ),
                            )
                        )

                        # Add subsection content
                        if len(subsection_parts) > 1:
                            subsection_content = subsection_parts[1].strip()
                            for paragraph in subsection_content.split("\n\n"):
                                if paragraph.strip():
                                    # Detect bullet points
                                    if paragraph.startswith(
                                        "- "
                                    ) or paragraph.startswith("* "):
                                        for line in paragraph.split("\n"):
                                            if line.strip():
                                                story.append(
                                                    Paragraph(
                                                        line,
                                                        (
                                                            error_text_style
                                                            if is_error_report
                                                            else normal_style
                                                        ),
                                                    )
                                                )
                                    else:
                                        story.append(
                                            Paragraph(
                                                paragraph,
                                                (
                                                    error_text_style
                                                    if is_error_report
                                                    else normal_style
                                                ),
                                            )
                                        )
                else:
                    # No subsections, process content normally
                    for paragraph in section_content.split("\n\n"):
                        if paragraph.strip():
                            # Detect bullet points
                            if paragraph.startswith("- ") or paragraph.startswith("* "):
                                for line in paragraph.split("\n"):
                                    if line.strip():
                                        story.append(
                                            Paragraph(
                                                line,
                                                (
                                                    error_text_style
                                                    if is_error_report
                                                    else normal_style
                                                ),
                                            )
                                        )
                            else:
                                story.append(
                                    Paragraph(
                                        paragraph,
                                        (
                                            error_text_style
                                            if is_error_report
                                            else normal_style
                                        ),
                                    )
                                )

        # Build the PDF
        doc.build(story)

        return output_path

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise
