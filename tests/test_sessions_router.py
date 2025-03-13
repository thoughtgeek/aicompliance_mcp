import pytest
from fastapi import status

class TestSessionsRouter:
    """Tests for the sessions router endpoints"""
    
    def test_get_session(self, test_client, mock_storage_service, sample_session_data):
        """Test getting a session by ID"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Send request
        response = test_client.get(f"/api/sessions/{sample_session_data['id']}")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == sample_session_data["id"]
        assert response.json()["document_type"] == sample_session_data["document_type"]
        assert "messages" in response.json()
        assert "document_state" in response.json()
        
        # Check that storage service was called with session ID
        mock_storage_service.get_session.assert_called_with(sample_session_data["id"])
    
    def test_get_nonexistent_session(self, test_client, mock_storage_service):
        """Test getting a non-existent session"""
        # Setup mock storage to return None (session not found)
        mock_storage_service.get_session.return_value = None
        
        # Send request
        response = test_client.get("/api/sessions/nonexistent-session-id")
        
        # Check response (should be 404 Not Found)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_list_sessions(self, test_client, mock_storage_service):
        """Test listing all sessions"""
        # Setup mock storage to return a list of session summaries
        mock_storage_service.list_sessions.return_value = [
            {
                "id": "test-session-id-1",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T01:00:00",
                "document_type": "EU AI Act Model Card"
            },
            {
                "id": "test-session-id-2",
                "created_at": "2023-01-02T00:00:00",
                "updated_at": "2023-01-02T01:00:00",
                "document_type": "US Model Risk Assessment"
            }
        ]
        
        # Send request
        response = test_client.get("/api/sessions/")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "test-session-id-1"
        assert response.json()[1]["id"] == "test-session-id-2"
        
        # Check that storage service was called
        mock_storage_service.list_sessions.assert_called_once()
    
    def test_list_sessions_with_user_filter(self, test_client, mock_storage_service):
        """Test listing sessions filtered by user ID"""
        # Setup mock storage to return a filtered list
        mock_storage_service.list_sessions.return_value = [
            {
                "id": "test-session-id-1",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T01:00:00",
                "document_type": "EU AI Act Model Card"
            }
        ]
        
        # Send request with user_id query parameter
        response = test_client.get("/api/sessions/?user_id=test-user-id")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1
        
        # Check that storage service was called with user_id
        mock_storage_service.list_sessions.assert_called_with("test-user-id")
    
    def test_delete_session(self, test_client, mock_storage_service):
        """Test deleting a session"""
        # Setup mock storage to return success
        mock_storage_service.delete_session.return_value = True
        
        # Send request
        response = test_client.delete("/api/sessions/test-session-id")
        
        # Check response (should be 204 No Content)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Check that storage service was called with session ID
        mock_storage_service.delete_session.assert_called_with("test-session-id")
    
    def test_delete_nonexistent_session(self, test_client, mock_storage_service):
        """Test deleting a non-existent session"""
        # Setup mock storage to return failure
        mock_storage_service.delete_session.return_value = False
        
        # Send request
        response = test_client.delete("/api/sessions/nonexistent-session-id")
        
        # Check response (should be 404 Not Found)
        assert response.status_code == status.HTTP_404_NOT_FOUND 