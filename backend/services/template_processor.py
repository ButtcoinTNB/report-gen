from docxtpl import DocxTemplate, RichText
import os
from pathlib import Path
import re
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from utils.error_handler import handle_exception, logger
from config import settings

class TemplateProcessor:
    """
    Utility class for processing DOCX templates with the docxtpl library.
    This class handles the dynamic insertion of variables into templates
    and supports rich text formatting.
    """
    
    def __init__(self):
        # Define template directories
        self.template_dirs = [
            Path("templates"),
            Path("backend/reference_reports"),
            Path("reference_reports"),
            Path(settings.UPLOAD_DIR) / "templates" if hasattr(settings, 'UPLOAD_DIR') else Path("uploads/templates")
        ]
        
        # Define output directory
        self.output_dir = Path(settings.GENERATED_REPORTS_DIR) if hasattr(settings, 'GENERATED_REPORTS_DIR') else Path("generated_reports")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize RichText instances for styled variables
        self.rich_text_fields = [
            "dinamica_eventi_accertamenti",
            "causa_danno",
            "lista_allegati"
        ]
    
    def find_template(self, template_name: str = "template.docx") -> Optional[Path]:
        """
        Find a template in the template directories.
        
        Args:
            template_name: Name of the template file to look for
            
        Returns:
            Path to the template file or None if not found
        """
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                logger.info(f"Found template at {template_path}")
                return template_path
        
        logger.warning(f"Template {template_name} not found")
        return None
    
    def _convert_to_rich_text(self, text: str) -> RichText:
        """
        Convert text with markdown-like syntax to RichText.
        
        Args:
            text: Text to convert
            
        Returns:
            RichText object with appropriate formatting
        """
        rt = RichText()
        
        # Split by bullet points
        if text.startswith("- "):
            lines = text.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith("- "):
                    content = line[2:].strip()
                    
                    # Add bullet symbol
                    rt.add("\u2022 ", bold=True)
                    
                    # Process the content for bold/italic
                    parts = re.finditer(r'(\*\*.*?\*\*|\*.*?\*|__.*?__|_.*?_|`.*?`|[^*_`]+)', content)
                    for part in parts:
                        match = part.group(0)
                        if match.startswith("**") and match.endswith("**"):
                            rt.add(match[2:-2], bold=True)
                        elif match.startswith("*") and match.endswith("*"):
                            rt.add(match[1:-1], italic=True)
                        elif match.startswith("__") and match.endswith("__"):
                            rt.add(match[2:-2], bold=True)
                        elif match.startswith("_") and match.endswith("_"):
                            rt.add(match[1:-1], italic=True)
                        elif match.startswith("`") and match.endswith("`"):
                            rt.add(match[1:-1], italic=True, color="404040")
                        else:
                            rt.add(match)
                    
                    # Add newline except for the last item
                    if i < len(lines) - 1:
                        rt.add("\n")
        else:
            # Process the content for bold/italic
            parts = re.finditer(r'(\*\*.*?\*\*|\*.*?\*|__.*?__|_.*?_|`.*?`|[^*_`]+)', text)
            for part in parts:
                match = part.group(0)
                if match.startswith("**") and match.endswith("**"):
                    rt.add(match[2:-2], bold=True)
                elif match.startswith("*") and match.endswith("*"):
                    rt.add(match[1:-1], italic=True)
                elif match.startswith("__") and match.endswith("__"):
                    rt.add(match[2:-2], bold=True)
                elif match.startswith("_") and match.endswith("_"):
                    rt.add(match[1:-1], italic=True)
                elif match.startswith("`") and match.endswith("`"):
                    rt.add(match[1:-1], italic=True, color="404040")
                else:
                    rt.add(match)
        
        return rt
    
    def process_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process variables to ensure proper formatting in the template.
        
        Args:
            variables: Dictionary of variables to process
            
        Returns:
            Processed variables dictionary
        """
        processed_vars = {}
        
        # Copy all variables
        for key, value in variables.items():
            processed_vars[key] = value
        
        # Process rich text fields
        for field in self.rich_text_fields:
            if field in variables and variables[field]:
                processed_vars[field] = self._convert_to_rich_text(str(variables[field]))
        
        # Format monetary values
        for key, value in variables.items():
            if key.startswith("totale_") or key == "valore_merce":
                if value and isinstance(value, str) and not value.startswith("Non fornito"):
                    # Ensure proper currency format
                    if not value.startswith("€"):
                        processed_vars[key] = f"€ {value}"
        
        # Format dates
        date_fields = ["data_sinistro", "data_fattura", "data_oggi"]
        for field in date_fields:
            if field in variables and variables[field] and variables[field] != "Non fornito":
                try:
                    # Try to parse the date if it's not already formatted
                    if not any(month in variables[field] for month in ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio"]):
                        date_parts = re.split(r'[/\-]', variables[field])
                        if len(date_parts) == 3:
                            day, month, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                            if year < 100:
                                year += 2000
                                
                            months_italian = [
                                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
                            ]
                            
                            if field == "data_oggi":
                                processed_vars[field] = f"{day} {months_italian[month-1]} {year}"
                except Exception as e:
                    logger.warning(f"Failed to parse date for {field}: {str(e)}")
        
        return processed_vars
    
    def render_template(self, template_name: str, variables: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Render a template with the provided variables.
        
        Args:
            template_name: Name of the template file
            variables: Dictionary of variables to insert
            output_path: Optional output path
            
        Returns:
            Path to the rendered document
        """
        try:
            # Find the template
            template_path = self.find_template(template_name)
            if not template_path:
                logger.error(f"Template {template_name} not found")
                raise FileNotFoundError(f"Template {template_name} not found")
            
            # Process variables
            processed_vars = self.process_variables(variables)
            
            # Generate output path if not provided
            if not output_path:
                report_id = str(uuid.uuid4())
                output_path = str(self.output_dir / f"report_{report_id}.docx")
            
            # Load the template
            doc = DocxTemplate(str(template_path))
            
            # Render the template with variables
            doc.render(processed_vars)
            
            # Save the document
            doc.save(output_path)
            
            logger.info(f"Successfully rendered template {template_name} to {output_path}")
            return output_path
            
        except Exception as e:
            handle_exception(e, "Template rendering")
            raise
    
    def analyze_template(self, template_name: str = "template.docx") -> List[str]:
        """
        Analyze a template to find all variables.
        
        Args:
            template_name: Name of the template to analyze
            
        Returns:
            List of variable names found in the template
        """
        try:
            # Find the template
            template_path = self.find_template(template_name)
            if not template_path:
                logger.error(f"Template {template_name} not found")
                return []
            
            # Load the template
            doc = DocxTemplate(str(template_path))
            
            # Get all variables
            variables = doc.get_undeclared_template_variables()
            
            logger.info(f"Found {len(variables)} variables in template {template_name}")
            return list(variables)
            
        except Exception as e:
            handle_exception(e, "Template analysis")
            return []

# Create a singleton instance
template_processor = TemplateProcessor() 