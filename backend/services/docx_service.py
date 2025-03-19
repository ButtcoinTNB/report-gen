from typing import Dict, Any, Optional
from docxtpl import DocxTemplate
import os
from pathlib import Path
from uuid import UUID
from pydantic import UUID4
from utils.error_handler import handle_exception, logger
from config import settings

class DocxService:
    def __init__(self):
        # Get current working directory for debugging
        cwd = os.getcwd()
        logger.info(f"Current working directory: {cwd}")
        
        # Define common paths - adjust paths to work in both development and production
        self.templates_dirs = [
            Path("reference_reports"),                # Direct reference_reports folder
            Path("templates"),                        # Direct templates folder
            Path(cwd) / "reference_reports",          # Absolute path using current working directory
            Path(cwd) / "backend" / "reference_reports" # Absolute path to backend/reference_reports
        ]
        
        # Define output directories
        self.output_dir = Path(settings.GENERATED_REPORTS_DIR)
        self.preview_dir = Path("previews")
        
        # Create necessary directories for outputs (these should always work)
        for directory in [self.output_dir, self.preview_dir]:
            try:
                directory.mkdir(exist_ok=True, parents=True)
                logger.info(f"Created or verified directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {str(e)}")
        
        # Try to create template directories, but don't fail if they can't be created
        for template_dir in self.templates_dirs:
            try:
                template_dir.mkdir(exist_ok=True, parents=True)
                logger.info(f"Created or verified template directory: {template_dir}")
            except Exception as e:
                # This is now just informational - not a warning
                logger.info(f"Note: Could not create template directory {template_dir}: {str(e)}")
                # Check if directory exists anyway (might be read-only)
                if template_dir.exists():
                    logger.info(f"Directory {template_dir} exists but cannot be created (might be read-only)")
    
    def find_template(self, template_name: str = "template.docx") -> Optional[Path]:
        """
        Find the template file in available template directories.
        
        Args:
            template_name: Name of the template file to use
            
        Returns:
            Path to the template file or None if not found
        """
        logger.info(f"Looking for template: {template_name}")
        
        # Check all potential template directories
        for template_dir in self.templates_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                logger.info(f"Found template at {template_path}")
                return template_path
            else:
                logger.debug(f"Template not found at {template_path}")
        
        # Special case for default template name
        if template_name == "default.docx" and self.find_template("template.docx"):
            return self.find_template("template.docx")
        
        # If no template found, look for any .docx files in the templates directories
        for template_dir in self.templates_dirs:
            if template_dir.exists():
                docx_files = list(template_dir.glob("*.docx"))
                if docx_files:
                    logger.info(f"Using alternative template: {docx_files[0]}")
                    return docx_files[0]
        
        logger.warning(f"No suitable template found for {template_name}")
        return None
    
    def generate_report(self, template_variables: Dict[str, Any], template_name: str = "template.docx") -> str:
        """
        Generate a DOCX report using the provided template and variables.
        
        Args:
            template_variables: Dictionary of variables to substitute in the template
            template_name: Name of the template file to use
            
        Returns:
            Path to the generated DOCX file
        """
        try:
            template_path = self.find_template(template_name)
            if not template_path:
                logger.warning(f"Template {template_name} not found, creating a basic document instead")
                # Create a basic template if none found
                from docx import Document
                basic_doc = Document()
                basic_doc.add_heading("Report", 0)
                
                # Create a temporary template file
                temp_template = self.output_dir / "temp_template.docx"
                basic_doc.save(str(temp_template))
                template_path = temp_template
            
            # Generate unique filename for the report
            report_id = str(UUID4())
            output_path = self.output_dir / f"report_{report_id}.docx"
            
            # Load template and render with variables
            doc = DocxTemplate(str(template_path))
            doc.render(template_variables)
            
            # Save generated report
            doc.save(str(output_path))
            
            logger.info(f"Generated report {report_id} using template {template_name}")
            return report_id
            
        except Exception as e:
            handle_exception(e, "DOCX generation")
            raise
    
    def get_report_path(self, report_id: UUID4) -> Path:
        """
        Get the path where a report should be stored.
        
        Args:
            report_id: UUID of the report
            
        Returns:
            Path where the report should be stored
        """
        return self.output_dir / f"report_{report_id}.docx"
    
    def get_preview_path(self, report_id: UUID4) -> Path:
        """Get the path where a preview should be stored"""
        return self.preview_dir / f"preview_{report_id}.html"
    
    def modify_report(self, report_id: UUID4, template_variables: Dict[str, Any]) -> str:
        """
        Modify an existing report with new template variables.
        
        Args:
            report_id: UUID of the report to modify
            template_variables: Variables to use in the template
            
        Returns:
            Path to the modified report file
        """
        report_path = self.get_report_path(report_id)
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")
            
        # Load the existing report as a template
        doc = DocxTemplate(report_path)
        
        # Render with new variables
        doc.render(template_variables)
        
        # Save to a new file
        new_path = self.output_dir / f"report_{report_id}_modified.docx"
        doc.save(new_path)
        
        return str(new_path)

# Create singleton instance
docx_service = DocxService() 