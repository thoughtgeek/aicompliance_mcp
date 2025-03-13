import pytest
from fastapi import status
import json

class TestChatRouter:
    """Tests for the chat router endpoints"""
    
    def test_process_message_new_session(self, test_client, mock_llm_service, mock_storage_service, mock_n8n_service):
        """Test processing a message when no session exists"""
        # Request data
        request_data = {
            "message": "I want to create an EU AI Act Model Card"
        }
        
        # Send request
        response = test_client.post("/api/chat/message", json=request_data)
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        assert "session_id" in response.json()
        assert response.json()["session_id"] == "test-session-id"
        
        # Check that LLM service was called
        mock_llm_service.analyze_message.assert_called_once()
        mock_llm_service.generate_response.assert_called_once()
        
        # Check that storage service was called
        mock_storage_service.save_session.assert_called_once()
    
    def test_process_message_existing_session(self, test_client, mock_llm_service, mock_storage_service, mock_n8n_service, sample_session_data):
        """Test processing a message with an existing session"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Request data
        request_data = {
            "session_id": "test-session-id",
            "message": "What is the primary purpose of my model?"
        }
        
        # Send request
        response = test_client.post("/api/chat/message", json=request_data)
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        assert "session_id" in response.json()
        assert response.json()["session_id"] == "test-session-id"
        
        # Check that storage service was called with session ID
        mock_storage_service.get_session.assert_called_with("test-session-id")
    
    def test_process_message_nonexistent_session(self, test_client, mock_storage_service):
        """Test processing a message with a non-existent session ID"""
        # Setup mock storage to return None (session not found)
        mock_storage_service.get_session.return_value = None
        
        # Request data
        request_data = {
            "session_id": "nonexistent-session-id",
            "message": "Hello"
        }
        
        # Send request
        response = test_client.post("/api/chat/message", json=request_data)
        
        # Check response (should be 404 Not Found)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_process_message_repository_analysis(self, test_client, mock_llm_service, mock_storage_service, mock_n8n_service):
        """Test processing a message for repository analysis"""
        # Mock LLM service to return connect_repository intent
        async def mock_analyze_repo_message(message, history):
            return "connect_repository", {"repository_url": "https://github.com/example/model"}
        
        mock_llm_service.analyze_message.side_effect = mock_analyze_repo_message
        
        # Request data
        request_data = {
            "message": "Analyze my repository at https://github.com/example/model"
        }
        
        # Send request
        response = test_client.post("/api/chat/message", json=request_data)
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        
        # Check that n8n service was called
        mock_n8n_service.analyze_repository.assert_called_once_with("https://github.com/example/model")
    
    def test_process_message_provide_information(self, test_client, mock_llm_service, mock_storage_service, mock_n8n_service, sample_session_data):
        """Test processing a message providing model information"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Mock LLM service to return provide_information intent
        async def mock_analyze_info_message(message, history):
            return "provide_information", {"model_name": "UpdatedModel", "model_version": "2.0"}
        
        mock_llm_service.analyze_message.side_effect = mock_analyze_info_message
        
        # Request data
        request_data = {
            "session_id": "test-session-id",
            "message": "My model is actually called UpdatedModel version 2.0"
        }
        
        # Send request
        response = test_client.post("/api/chat/message", json=request_data)
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        
        # Check that the document state was updated
        # This is tricky to verify since we're not directly accessing the stored state
        # We can check that save_session was called, which implies the state was updated
        mock_storage_service.save_session.assert_called_once()
    
    def test_process_message_request_export(self, test_client, mock_llm_service, mock_storage_service, mock_n8n_service, sample_session_data):
        """Test processing a message requesting document export"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Mock LLM service to return request_export intent
        async def mock_analyze_export_message(message, history):
            return "request_export", {}
        
        mock_llm_service.analyze_message.side_effect = mock_analyze_export_message
        
        # Request data
        request_data = {
            "session_id": "test-session-id",
            "message": "Can I export the document now?"
        }
        
        # Send request
        response = test_client.post("/api/chat/message", json=request_data)
        
        # Check response
        assert response.status_code == status.HTTP_200_OK 