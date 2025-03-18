from typing import Dict, Any
from docxtpl import DocxTemplate
import os
from pathlib import Path
import uuid
from utils.error_handler import handle_exception, logger

class DocxService:
    def __init__(self):
        self.templates_dir = Path("templates")
        self.output_dir = Path("generated_reports")
        self.preview_dir = Path("previews")
        
        # Create necessary directories
        for directory in [self.templates_dir, self.output_dir, self.preview_dir]:
            directory.mkdir(exist_ok=True)
    
    def generate_report(self, template_variables: Dict[str, Any], template_name: str = "default.docx") -> str:
        """
        Generate a DOCX report using the provided template and variables.
        
        Args:
            template_variables: Dictionary of variables to substitute in the template
            template_name: Name of the template file to use
            
        Returns:
            Path to the generated DOCX file
        """
        try:
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                raise FileNotFoundError(f"Template {template_name} not found")
            
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