from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import logging
import io

from ..models.document import ExportFormat, ExportRequest
from ..services.storage import StorageService
from ..services.template import TemplateService

router = APIRouter(prefix="/documents")
logger = logging.getLogger(__name__)

# Service dependencies
def get_storage_service():
    return StorageService()

def get_template_service():
    return TemplateService()

@router.get("/{session_id}/export", response_class=StreamingResponse)
async def export_document(
    session_id: str,
    format: ExportFormat = ExportFormat.PDF,
    storage_service: StorageService = Depends(get_storage_service),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Export a document based on the session's document state
    """
    try:
        # Get session data
        session_data = await storage_service.get_session(session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
            
        # Check if document state exists
        if not session_data.get("document_state") or not session_data["document_state"].get("data"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No document data available for export"
            )
        
        # Get document type and data
        document_type = session_data.get("document_type", "EU AI Act Model Card")
        document_data = session_data["document_state"].get("data", {})
        
        # Determine file extension and media type based on format
        file_extension = ""
        media_type = ""
        
        if format == ExportFormat.PDF:
            file_extension = "pdf"
            media_type = "application/pdf"
        elif format == ExportFormat.HTML:
            file_extension = "html"
            media_type = "text/html"
        elif format == ExportFormat.MARKDOWN:
            file_extension = "md"
            media_type = "text/markdown"
        
        # Generate content based on format
        file_content = None
        filename = f"{document_type.replace(' ', '_')}_{session_id}.{file_extension}"
        
        if format == ExportFormat.PDF:
            # Render HTML then convert to PDF
            html_content = template_service.render_document("model_card", document_data)
            file_content = template_service.generate_pdf(html_content)
            
        elif format == ExportFormat.HTML:
            # Render HTML directly
            html_content = template_service.render_document("model_card", document_data)
            file_content = html_content.encode('utf-8')
            
        elif format == ExportFormat.MARKDOWN:
            # Generate Markdown
            md_content = template_service.generate_markdown(document_data)
            file_content = md_content.encode('utf-8')
            
        # Create response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting document for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting document: {str(e)}"
        )

@router.get("/templates")
async def list_document_templates():
    """
    List available document templates
    """
    try:
        # This would typically be retrieved from a database or config
        templates = {
            "EU AI Act Model Card": {
                "description": "Model card template compliant with EU AI Act requirements",
                "sections": [
                    "model_details",
                    "intended_use",
                    "risk_assessment",
                    "performance_metrics",
                    "training_data",
                    "technical_specifications",
                    "human_oversight",
                    "compliance_information",
                    "contact_information"
                ]
            },
            "US Model Risk Assessment": {
                "description": "Model risk assessment template for US regulatory compliance",
                "sections": [
                    "model_details",
                    "model_development",
                    "validation_results",
                    "performance_metrics",
                    "monitoring_plan",
                    "governance_framework",
                    "risk_controls"
                ]
            },
            "General Model Card": {
                "description": "Generic model card template for AI model documentation",
                "sections": [
                    "model_details",
                    "intended_use",
                    "limitations",
                    "performance_metrics",
                    "training_data",
                    "ethical_considerations"
                ]
            }
        }
        
        return templates
        
    except Exception as e:
        logger.error(f"Error listing document templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing document templates: {str(e)}"
        )

@router.get("/{session_id}/status")
async def get_document_status(
    session_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Get the completion status of a document
    """
    try:
        # Get session data
        session_data = await storage_service.get_session(session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
            
        # Check if document state exists
        if not session_data.get("document_state"):
            return {
                "document_type": session_data.get("document_type"),
                "completion_percentage": 0,
                "completion_status": {},
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at")
            }
        
        # Calculate completion percentage
        completion_status = session_data["document_state"].get("completion_status", {})
        completion_percentage = 0
        
        if completion_status:
            completed = sum(1 for status in completion_status.values() if status)
            total = len(completion_status)
            completion_percentage = (completed / total) * 100 if total > 0 else 0
        
        return {
            "document_type": session_data.get("document_type"),
            "completion_percentage": completion_percentage,
            "completion_status": completion_status,
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document status: {str(e)}"
        ) 