import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
from typing import Dict, Any

from app.main import app
from app.services.llm import LLMService
from app.services.storage import StorageService
from app.services.n8n import N8nService
from app.services.template import TemplateService

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)

@pytest.fixture
def mock_llm_service():
    """Mock LLMService to avoid making real API calls"""
    with patch('app.routers.chat.get_llm_service') as mock_get_service:
        service = AsyncMock(spec=LLMService)
        
        # Mock analyze_message method
        async def mock_analyze_message(message, history):
            # Return different intents based on message contents for testing
            if "create" in message.lower() or "document" in message.lower():
                return "select_document_type", {"document_type": "EU AI Act Model Card"}
            elif "repository" in message.lower() or "github" in message.lower():
                return "connect_repository", {"repository_url": "https://github.com/example/model"}
            elif "export" in message.lower() or "download" in message.lower():
                return "request_export", {}
            else:
                return "provide_information", {"model_name": "TestModel", "model_version": "1.0"}
        
        service.analyze_message.side_effect = mock_analyze_message
        
        # Mock determine_next_question method
        async def mock_determine_next_question(document_state):
            return "What is the primary purpose of your model?"
        
        service.determine_next_question.side_effect = mock_determine_next_question
        
        # Mock generate_response method
        async def mock_generate_response(intent, entities, document_state, document_templates=None):
            if intent == "select_document_type":
                return "I'll help you create an EU AI Act Model Card. Let's start gathering information about your model."
            elif intent == "connect_repository":
                return "I'll analyze your GitHub repository to extract model information."
            elif intent == "provide_information":
                return "Thanks for providing information about your model."
            elif intent == "request_export":
                return "Your document is ready for export."
            else:
                return "I'm here to help you create compliance documentation."
        
        service.generate_response.side_effect = mock_generate_response
        
        mock_get_service.return_value = service
        yield service

@pytest.fixture
def mock_storage_service():
    """Mock StorageService to avoid making real database calls"""
    with patch('app.routers.chat.get_storage_service') as mock_get_service:
        service = AsyncMock(spec=StorageService)
        
        # In-memory storage for testing
        memory_storage = {}
        
        # Mock get_session method
        async def mock_get_session(session_id):
            return memory_storage.get(session_id)
        
        service.get_session.side_effect = mock_get_session
        
        # Mock save_session method
        async def mock_save_session(session_data):
            if "id" not in session_data or not session_data["id"]:
                session_data["id"] = "test-session-id"
            memory_storage[session_data["id"]] = session_data
            return session_data["id"]
        
        service.save_session.side_effect = mock_save_session
        
        # Mock list_sessions method
        async def mock_list_sessions(user_id=None):
            return [
                {"id": session_id, "created_at": session["created_at"], "updated_at": session["updated_at"], "document_type": session.get("document_type")}
                for session_id, session in memory_storage.items()
                if not user_id or session.get("user_id") == user_id
            ]
        
        service.list_sessions.side_effect = mock_list_sessions
        
        # Mock delete_session method
        async def mock_delete_session(session_id):
            if session_id in memory_storage:
                del memory_storage[session_id]
                return True
            return False
        
        service.delete_session.side_effect = mock_delete_session
        
        mock_get_service.return_value = service
        yield service

@pytest.fixture
def mock_n8n_service():
    """Mock N8nService to avoid making real API calls"""
    with patch('app.routers.chat.get_n8n_service') as mock_get_service:
        service = AsyncMock(spec=N8nService)
        
        # Mock analyze_repository method
        async def mock_analyze_repository(repo_url):
            # Return mock repository data
            return {
                "model_name": "TestModel",
                "model_version": "1.0",
                "model_description": "A test model for documentation generation",
                "model_framework": "PyTorch",
                "model_license": "MIT",
                "model_inputs": ["image"],
                "model_outputs": ["classification"],
                "dependencies": ["torch", "numpy", "transformers"]
            }
        
        service.analyze_repository.side_effect = mock_analyze_repository
        
        mock_get_service.return_value = service
        yield service

@pytest.fixture
def mock_template_service():
    """Mock TemplateService to avoid file system operations"""
    with patch('app.routers.documents.get_template_service') as mock_get_service:
        service = MagicMock(spec=TemplateService)
        
        # Mock render_document method
        def mock_render_document(template_name, data):
            return "<html><body>Mock document content</body></html>"
        
        service.render_document.side_effect = mock_render_document
        
        # Mock generate_pdf method
        def mock_generate_pdf(html_content, css_file=None):
            return b"Mock PDF content"
        
        service.generate_pdf.side_effect = mock_generate_pdf
        
        # Mock generate_markdown method
        def mock_generate_markdown(data, template_name="model_card_md"):
            return "# Mock Markdown Content"
        
        service.generate_markdown.side_effect = mock_generate_markdown
        
        mock_get_service.return_value = service
        yield service

@pytest.fixture
def sample_document_state():
    """Sample document state for testing"""
    return {
        "type": "EU AI Act Model Card",
        "data": {
            "model_details": {
                "name": "TestModel",
                "version": "1.0",
                "description": "A test model for documentation generation",
                "framework": "PyTorch",
                "license": "MIT"
            },
            "intended_use": {
                "primary_purpose": "Image classification",
                "intended_users": ["Researchers", "Developers"],
                "use_cases": ["Product categorization", "Content moderation"]
            },
            "technical_specifications": {
                "input_format": "image",
                "output_format": "classification",
                "dependencies": ["torch", "numpy", "transformers"]
            }
        },
        "completion_status": {
            "model_details": True,
            "intended_use": True,
            "technical_specifications": True,
            "risk_assessment": False,
            "performance_metrics": False,
            "training_data": False,
            "human_oversight": False,
            "compliance_information": False,
            "contact_information": False
        }
    }

@pytest.fixture
def sample_session_data(sample_document_state):
    """Sample session data for testing"""
    return {
        "id": "test-session-id",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T01:00:00",
        "document_type": "EU AI Act Model Card",
        "document_state": sample_document_state,
        "messages": [
            {
                "role": "user",
                "content": "I want to create an EU AI Act Model Card",
                "timestamp": "2023-01-01T00:00:00"
            },
            {
                "role": "assistant",
                "content": "I'll help you create an EU AI Act Model Card. Let's start gathering information about your model.",
                "timestamp": "2023-01-01T00:00:01"
            },
            {
                "role": "user",
                "content": "My model is called TestModel version 1.0",
                "timestamp": "2023-01-01T00:01:00"
            },
            {
                "role": "assistant",
                "content": "Thanks for providing information about your model.",
                "timestamp": "2023-01-01T00:01:01"
            }
        ]
    } 