from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4

class Message(BaseModel):
    """A single message in a conversation"""
    role: str = Field(..., description="Role of the message sender, either 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the message was sent")

class MessageRequest(BaseModel):
    """Request model for sending a new message"""
    session_id: Optional[str] = Field(None, description="Session ID. If not provided, a new session will be created")
    message: str = Field(..., description="User message content")

class MessageResponse(BaseModel):
    """Response model for a message"""
    message: str = Field(..., description="AI response")
    document_update: Dict[str, Any] = Field(default_factory=dict, description="Document state update")
    session_id: str = Field(..., description="Session ID")

class Session(BaseModel):
    """A conversation session with document state"""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Session ID")
    created_at: datetime = Field(default_factory=datetime.now, description="When the session was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When the session was last updated")
    messages: List[Message] = Field(default_factory=list, description="List of messages in the session")
    document_state: Dict[str, Any] = Field(default_factory=dict, description="Current state of the document being created")
    document_type: Optional[str] = Field(None, description="Type of document being created")
    user_id: Optional[str] = Field(None, description="User ID if authentication is enabled")

class SessionSummary(BaseModel):
    """Summary of a session for listing"""
    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="When the session was created")
    updated_at: datetime = Field(..., description="When the session was last updated")
    document_type: Optional[str] = Field(None, description="Type of document being created")
    completion_percentage: Optional[float] = Field(None, description="Percentage of document completion") 