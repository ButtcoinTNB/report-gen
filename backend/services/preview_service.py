from pathlib import Path
import mammoth
import asyncio
from uuid import UUID
from pydantic import UUID4
from utils.error_handler import handle_exception, logger
from services.docx_service import docx_service

class PreviewService:
    def __init__(self):
        self.preview_dir = Path("previews")
        self.preview_dir.mkdir(exist_ok=True)
        
        # Enhanced style map for better document structure
        self.style_map = """
        p[style-name='Title'] => h1.document-title:fresh
        p[style-name='Heading 1'] => h2.section-title:fresh
        p[style-name='Heading 2'] => h3.subsection-title:fresh
        p[style-name='Heading 3'] => h4.subsection-title:fresh
        p[style-name='Normal'] => p:fresh
        r[style-name='Strong'] => strong
        r[style-name='Emphasis'] => em
        table => table.document-table
        tr => tr
        td => td
        p[style-name='List Paragraph'] => li
        """
    
    async def generate_preview(self, report_id: UUID4) -> str:
        """
        Generate an enhanced HTML preview of a DOCX report.
        
        Args:
            report_id: UUID of the report to preview
            
        Returns:
            Path to the HTML preview file
        """
        try:
            # Get paths
            docx_path = docx_service.get_report_path(report_id)
            preview_path = docx_service.get_preview_path(report_id)
            
            # Convert DOCX to HTML with enhanced options
            with open(docx_path, 'rb') as docx_file:
                result = mammoth.convert_to_html(
                    docx_file,
                    style_map=self.style_map,
                    convert_image=mammoth.images.img_element(lambda image: {
                        "src": f"data:{image.content_type};base64,{image.base64_bytes.decode('utf-8')}",
                        "class": "document-image"
                    })
                )
            
            # Add enhanced styles and responsive design
            html_content = f"""
            <!DOCTYPE html>
            <html lang="it">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Anteprima Report</title>
                <style>
                    :root {{
                        --primary-color: #2c3e50;
                        --secondary-color: #34495e;
                        --background-color: #f8f9fa;
                        --text-color: #2c3e50;
                        --border-color: #dee2e6;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                        line-height: 1.6;
                        max-width: 1000px;
                        margin: 0 auto;
                        padding: 2rem;
                        background-color: var(--background-color);
                        color: var(--text-color);
                    }}
                    
                    .preview-container {{
                        background-color: white;
                        padding: 3rem;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    
                    .document-title {{
                        color: var(--primary-color);
                        font-size: 2.5rem;
                        margin-bottom: 2rem;
                        text-align: center;
                        border-bottom: 2px solid var(--border-color);
                        padding-bottom: 1rem;
                    }}
                    
                    .section-title {{
                        color: var(--primary-color);
                        font-size: 1.8rem;
                        margin-top: 2.5rem;
                        margin-bottom: 1.5rem;
                        border-bottom: 1px solid var(--border-color);
                        padding-bottom: 0.5rem;
                    }}
                    
                    .subsection-title {{
                        color: var(--secondary-color);
                        font-size: 1.4rem;
                        margin-top: 2rem;
                        margin-bottom: 1rem;
                    }}
                    
                    p {{
                        margin-bottom: 1rem;
                        text-align: justify;
                    }}
                    
                    .document-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 1.5rem 0;
                        background-color: white;
                    }}
                    
                    .document-table th,
                    .document-table td {{
                        border: 1px solid var(--border-color);
                        padding: 12px;
                        text-align: left;
                    }}
                    
                    .document-table th {{
                        background-color: var(--background-color);
                        font-weight: 600;
                    }}
                    
                    .document-table tr:nth-child(even) {{
                        background-color: var(--background-color);
                    }}
                    
                    .document-image {{
                        max-width: 100%;
                        height: auto;
                        margin: 1.5rem 0;
                        border-radius: 4px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    
                    @media print {{
                        body {{
                            background-color: white;
                            padding: 0;
                        }}
                        
                        .preview-container {{
                            box-shadow: none;
                            padding: 0;
                        }}
                    }}
                    
                    @media (max-width: 768px) {{
                        body {{
                            padding: 1rem;
                        }}
                        
                        .preview-container {{
                            padding: 1.5rem;
                        }}
                        
                        .document-title {{
                            font-size: 2rem;
                        }}
                        
                        .section-title {{
                            font-size: 1.5rem;
                        }}
                        
                        .subsection-title {{
                            font-size: 1.2rem;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="preview-container">
                    {result.value}
                </div>
                <script>
                    // Add table responsiveness
                    document.querySelectorAll('table').forEach(table => {{
                        const wrapper = document.createElement('div');
                        wrapper.style.overflowX = 'auto';
                        table.parentNode.insertBefore(wrapper, table);
                        wrapper.appendChild(table);
                    }});
                </script>
            </body>
            </html>
            """
            
            # Save the HTML preview
            preview_path.write_text(html_content, encoding='utf-8')
            
            # Log any warnings
            if result.messages:
                for message in result.messages:
                    logger.warning(f"Preview warning for {report_id}: {message}")
            
            logger.info(f"Generated enhanced preview for report {report_id}")
            return str(preview_path)
            
        except Exception as e:
            handle_exception(e, "Preview generation")
            raise
    
    def cleanup_old_previews(self, max_age_hours: int = 24):
        """Clean up preview files older than the specified age."""
        try:
            import time
            current_time = time.time()
            
            for preview_file in self.preview_dir.glob("*.html"):
                file_age_hours = (current_time - preview_file.stat().st_mtime) / 3600
                if file_age_hours > max_age_hours:
                    preview_file.unlink()
                    logger.info(f"Cleaned up old preview: {preview_file.name}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up previews: {str(e)}")

# Create singleton instance
preview_service = PreviewService() 