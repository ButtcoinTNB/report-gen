from typing import Dict, Any
from docxtpl import DocxTemplate
import os
from pathlib import Path
import uuid
from utils.error_handler import handle_exception, logger
from config import settings

class DocxService:
    def __init__(self):
        # Define possible template directories
        self.templates_dirs = [
            Path("templates"),                     # For local development
            Path("backend/reference_reports"),     # For template.docx standard location
            Path("reference_reports"),             # Alternative location
            Path(settings.UPLOAD_DIR) / "templates"  # User-uploaded templates
        ]
        self.output_dir = Path(settings.GENERATED_REPORTS_DIR) if hasattr(settings, 'GENERATED_REPORTS_DIR') else Path("generated_reports")
        self.preview_dir = Path("previews")
        
        # Create necessary directories
        for directory in [self.output_dir, self.preview_dir]:
            directory.mkdir(exist_ok=True)
        
        # Try to create template directories if they don't exist
        for template_dir in self.templates_dirs:
            try:
                template_dir.mkdir(exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create template directory {template_dir}: {str(e)}")
    
    def find_template(self, template_name: str = "template.docx") -> Path:
        """
        Find the template file in available template directories.
        
        Args:
            template_name: Name of the template file to use
            
        Returns:
            Path to the template file or None if not found
        """
        # Check all potential template directories
        for template_dir in self.templates_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                logger.info(f"Found template at {template_path}")
                return template_path
        
        # Special case for default template name
        if template_name == "default.docx" and self.find_template("template.docx"):
            return self.find_template("template.docx")
        
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
            report_id = str(uuid.uuid4())
            output_path = self.output_dir / f"{report_id}.docx"
            
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
    
    def get_report_path(self, report_id: str) -> Path:
        """Get the full path to a generated report."""
        report_path = self.output_dir / f"{report_id}.docx"
        if not report_path.exists():
            raise FileNotFoundError(f"Report {report_id} not found")
        return report_path
    
    def get_preview_path(self, report_id: str) -> Path:
        """Get the path where the preview should be stored."""
        return self.preview_dir / f"{report_id}.html"
    
    def modify_report(self, report_id: str, template_variables: Dict[str, Any]) -> str:
        """
        Modify an existing report with new variables.
        
        Args:
            report_id: ID of the report to modify
            template_variables: New variables to use
            
        Returns:
            New report ID
        """
        try:
            # Get the original report path
            original_path = self.get_report_path(report_id)
            
            # Generate new report ID
            new_report_id = str(uuid.uuid4())
            new_path = self.output_dir / f"{new_report_id}.docx"
            
            # Load the original as template and re-render with new variables
            doc = DocxTemplate(str(original_path))
            doc.render(template_variables)
            doc.save(str(new_path))
            
            logger.info(f"Modified report {report_id} -> {new_report_id}")
            return new_report_id
            
        except Exception as e:
            handle_exception(e, "DOCX modification")
            raise

# Create singleton instance
docx_service = DocxService() 