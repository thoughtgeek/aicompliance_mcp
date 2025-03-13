import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
import requests

from app.services.llm import LLMService

@pytest.fixture
def mock_requests_post():
    """Mock the requests.post function"""
    with patch('requests.post') as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generated_text": "Mock LLM response"}
        mock_post.return_value = mock_response
        yield mock_post

class TestLLMService:
    """Tests for the LLM service"""
    
    async def test_analyze_message_document_type_intent(self, mock_requests_post):
        """Test analyzing message with document type intent"""
        # Create instance of LLMService
        service = LLMService()
        
        # Mock the _parse_llm_response method
        service._parse_llm_response = MagicMock(return_value={
            "intent": "select_document_type",
            "entities": {"document_type": "EU AI Act Model Card"}
        })
        
        # Test message and history
        message = "I want to create an EU AI Act Model Card"
        history = []
        
        # Call the method
        intent, entities = await service.analyze_message(message, history)
        
        # Check result
        assert intent == "select_document_type"
        assert entities == {"document_type": "EU AI Act Model Card"}
        
        # Check that requests.post was called
        mock_requests_post.assert_called_once()
    
    async def test_analyze_message_repository_intent(self, mock_requests_post):
        """Test analyzing message with repository intent"""
        # Create instance of LLMService
        service = LLMService()
        
        # Mock the _parse_llm_response method
        service._parse_llm_response = MagicMock(return_value={
            "intent": "connect_repository",
            "entities": {"repository_url": "https://github.com/example/model"}
        })
        
        # Test message and history
        message = "Analyze my repository at https://github.com/example/model"
        history = []
        
        # Call the method
        intent, entities = await service.analyze_message(message, history)
        
        # Check result
        assert intent == "connect_repository"
        assert entities == {"repository_url": "https://github.com/example/model"}
    
    async def test_analyze_message_information_intent(self, mock_requests_post):
        """Test analyzing message with information intent"""
        # Create instance of LLMService
        service = LLMService()
        
        # Mock the _parse_llm_response method
        service._parse_llm_response = MagicMock(return_value={
            "intent": "provide_information",
            "entities": {"model_name": "TestModel", "model_version": "1.0"}
        })
        
        # Test message and history
        message = "My model is called TestModel version 1.0"
        history = []
        
        # Call the method
        intent, entities = await service.analyze_message(message, history)
        
        # Check result
        assert intent == "provide_information"
        assert entities == {"model_name": "TestModel", "model_version": "1.0"}
    
    async def test_analyze_message_export_intent(self, mock_requests_post):
        """Test analyzing message with export intent"""
        # Create instance of LLMService
        service = LLMService()
        
        # Mock the _parse_llm_response method
        service._parse_llm_response = MagicMock(return_value={
            "intent": "request_export",
            "entities": {}
        })
        
        # Test message and history
        message = "Can I export the document now?"
        history = []
        
        # Call the method
        intent, entities = await service.analyze_message(message, history)
        
        # Check result
        assert intent == "request_export"
        assert entities == {}
    
    async def test_analyze_message_api_error(self, mock_requests_post):
        """Test analyzing message when API returns an error"""
        # Create instance of LLMService
        service = LLMService()
        
        # Mock requests.post to raise an exception
        mock_requests_post.side_effect = Exception("API error")
        
        # Test message and history
        message = "Hello"
        history = []
        
        # Call the method
        intent, entities = await service.analyze_message(message, history)
        
        # Check result (should fall back to general query)
        assert intent == "general_query"
        assert entities == {}
    
    async def test_determine_next_question(self, mock_requests_post):
        """Test determining the next question based on document state"""
        # Create instance of LLMService
        service = LLMService()
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generated_text": "What is the primary purpose of your model?"}
        mock_requests_post.return_value = mock_response
        
        # Test document state
        document_state = {
            "type": "EU AI Act Model Card",
            "data": {
                "model_details": {
                    "name": "TestModel",
                    "version": "1.0"
                }
            },
            "completion_status": {
                "model_details": True,
                "intended_use": False
            }
        }
        
        # Call the method
        question = await service.determine_next_question(document_state)
        
        # Check result
        assert isinstance(question, str)
        assert len(question) > 0
    
    async def test_generate_response(self, mock_requests_post):
        """Test generating a response based on intent and entities"""
        # Create instance of LLMService
        service = LLMService()
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generated_text": "I'll help you create an EU AI Act Model Card."}
        mock_requests_post.return_value = mock_response
        
        # Test intent, entities, and document state
        intent = "select_document_type"
        entities = {"document_type": "EU AI Act Model Card"}
        document_state = {}
        
        # Call the method
        response = await service.generate_response(intent, entities, document_state)
        
        # Check result
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_parse_llm_response_valid_json(self):
        """Test parsing LLM response with valid JSON"""
        # Create instance of LLMService
        service = LLMService()
        
        # Test response with JSON
        response = '{"intent": "select_document_type", "entities": {"document_type": "EU AI Act Model Card"}}'
        
        # Call the method
        parsed = service._parse_llm_response(response)
        
        # Check result
        assert parsed == {
            "intent": "select_document_type",
            "entities": {"document_type": "EU AI Act Model Card"}
        }
    
    def test_parse_llm_response_invalid_json(self):
        """Test parsing LLM response with invalid JSON"""
        # Create instance of LLMService
        service = LLMService()
        
        # Test response without JSON
        response = "I'll help you create a document for your model."
        
        # Call the method
        parsed = service._parse_llm_response(response)
        
        # Check result (should extract intent from text)
        assert "intent" in parsed
        assert "entities" in parsed
    
    def test_calculate_completion(self):
        """Test calculating document completion percentage"""
        # Create instance of LLMService
        service = LLMService()
        
        # Test document state
        document_state = {
            "completion_status": {
                "model_details": True,
                "intended_use": True,
                "risk_assessment": False,
                "performance_metrics": False
            }
        }
        
        # Call the method
        completion = service._calculate_completion(document_state)
        
        # Check result (2 out of 4 = 50%)
        assert completion == 50.0 