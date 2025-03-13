from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class DocumentType(str, Enum):
    """Available document types in the system"""
    EU_AI_ACT_MODEL_CARD = "EU AI Act Model Card"
    US_MODEL_RISK_ASSESSMENT = "US Model Risk Assessment"
    GENERAL_MODEL_CARD = "General Model Card"

class DocumentField(BaseModel):
    """A field in a document section"""
    name: str
    description: str
    required: bool = True
    value: Optional[Any] = None

class DocumentSection(BaseModel):
    """A section in a document with multiple fields"""
    name: str
    description: str
    fields: Dict[str, DocumentField]
    completed: bool = False

class Document(BaseModel):
    """A document with full state information"""
    type: DocumentType
    data: Dict[str, Any] = Field(default_factory=dict, description="Document data with sections and fields")
    completion_status: Dict[str, bool] = Field(default_factory=dict, description="Completion status for each section")
    
    def get_completion_percentage(self) -> float:
        """Calculate the document completion percentage"""
        if not self.completion_status:
            return 0.0
        
        completed = sum(1 for status in self.completion_status.values() if status)
        total = len(self.completion_status)
        
        return (completed / total) * 100 if total > 0 else 0.0

class DocumentTemplate(BaseModel):
    """Document template definition"""
    type: DocumentType
    sections: List[DocumentSection]
    description: str

class ExportFormat(str, Enum):
    """Available export formats"""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"

class ExportRequest(BaseModel):
    """Request for document export"""
    session_id: str
    format: ExportFormat = ExportFormat.PDF 