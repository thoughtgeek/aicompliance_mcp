import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO, Union
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
import markdown

logger = logging.getLogger(__name__)

class TemplateService:
    def __init__(self):
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['format_date'] = lambda dt: dt.strftime('%Y-%m-%d') if dt else ''
        
        # Check if templates directory exists
        if not os.path.exists(template_dir):
            logger.warning(f"Templates directory not found at {template_dir}")
        
    def render_document(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render a document template with the provided data.
        
        Args:
            template_name: Name of the template file (e.g., "model_card.html")
            data: Dictionary containing the data to render in the template
            
        Returns:
            The rendered HTML content
        """
        try:
            # Add timestamp to the template context
            context = {
                "data": data,
                "generated_at": datetime.now(),
                "version": "1.0"
            }
            
            # Get the template
            template = self.env.get_template(f"{template_name}.html")
            
            # Render the template
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}")
            # Return a basic error template
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Error Rendering Document</title></head>
            <body>
                <h1>Error Rendering Document</h1>
                <p>There was an error generating your document. Please try again later.</p>
                <p>Error details: {str(e)}</p>
            </body>
            </html>
            """
    
    def generate_pdf(self, html_content: str, css_file: Optional[str] = None) -> bytes:
        """
        Generate a PDF from HTML content.
        
        Args:
            html_content: The HTML content to convert to PDF
            css_file: Optional path to a CSS file for styling
            
        Returns:
            The PDF file as bytes
        """
        try:
            # Create a temporary file for the HTML
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                temp_html.write(html_content.encode('utf-8'))
                temp_html_path = temp_html.name
            
            # Set up CSS
            stylesheets = []
            if css_file and os.path.exists(css_file):
                stylesheets.append(CSS(filename=css_file))
            
            # Generate PDF from the HTML file
            html = HTML(filename=temp_html_path)
            pdf_bytes = html.write_pdf(stylesheets=stylesheets)
            
            # Clean up the temporary file
            os.unlink(temp_html_path)
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise
    
    def generate_markdown(self, data: Dict[str, Any], template_name: str = "model_card_md") -> str:
        """
        Generate markdown content from template and data.
        
        Args:
            data: Dictionary containing the data to render in the template
            template_name: Name of the markdown template file
            
        Returns:
            The rendered markdown content
        """
        try:
            context = {
                "data": data,
                "generated_at": datetime.now(),
                "version": "1.0"
            }
            
            # Get the template
            template = self.env.get_template(f"{template_name}.md")
            
            # Render the template
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Error generating markdown: {str(e)}")
            return f"""
            # Error Generating Document
            
            There was an error generating your document. Please try again later.
            
            Error details: {str(e)}
            """
    
    def markdown_to_html(self, md_content: str) -> str:
        """
        Convert markdown content to HTML.
        
        Args:
            md_content: Markdown content
            
        Returns:
            HTML content
        """
        try:
            # Convert markdown to HTML
            html_content = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code']
            )
            
            # Wrap in a basic HTML document
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Generated Document</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; }}
                    th {{ background-color: #f2f2f2; text-align: left; }}
                    code {{ background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
                    pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }}
                </style>
            </head>
            <body>
                {html_content}
                <footer>
                    <p><small>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} using AI Compliance Documentation Generator</small></p>
                </footer>
            </body>
            </html>
            """
            
        except Exception as e:
            logger.error(f"Error converting markdown to HTML: {str(e)}")
            return f"<html><body><h1>Error Converting Document</h1><p>{str(e)}</p></body></html>" 