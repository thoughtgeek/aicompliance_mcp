import pytest
from fastapi import status
from app.models.document import ExportFormat

class TestDocumentsRouter:
    """Tests for the documents router endpoints"""
    
    def test_export_document_pdf(self, test_client, mock_storage_service, mock_template_service, sample_session_data):
        """Test exporting a document as PDF"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Send request
        response = test_client.get(f"/api/documents/{sample_session_data['id']}/export?format={ExportFormat.PDF}")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Content-Type"] == "application/pdf"
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        assert response.content == b"Mock PDF content"
        
        # Check that services were called
        mock_storage_service.get_session.assert_called_with(sample_session_data["id"])
        mock_template_service.render_document.assert_called_once()
        mock_template_service.generate_pdf.assert_called_once()
    
    def test_export_document_html(self, test_client, mock_storage_service, mock_template_service, sample_session_data):
        """Test exporting a document as HTML"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Send request
        response = test_client.get(f"/api/documents/{sample_session_data['id']}/export?format={ExportFormat.HTML}")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Content-Type"] == "text/html"
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        
        # Check that services were called
        mock_storage_service.get_session.assert_called_with(sample_session_data["id"])
        mock_template_service.render_document.assert_called_once()
    
    def test_export_document_markdown(self, test_client, mock_storage_service, mock_template_service, sample_session_data):
        """Test exporting a document as Markdown"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Send request
        response = test_client.get(f"/api/documents/{sample_session_data['id']}/export?format={ExportFormat.MARKDOWN}")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Content-Type"] == "text/markdown"
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        
        # Check that services were called
        mock_storage_service.get_session.assert_called_with(sample_session_data["id"])
        mock_template_service.generate_markdown.assert_called_once()
    
    def test_export_nonexistent_session(self, test_client, mock_storage_service):
        """Test exporting a document for a non-existent session"""
        # Setup mock storage to return None (session not found)
        mock_storage_service.get_session.return_value = None
        
        # Send request
        response = test_client.get("/api/documents/nonexistent-session-id/export")
        
        # Check response (should be 404 Not Found)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_export_empty_document(self, test_client, mock_storage_service):
        """Test exporting a document with no document state"""
        # Setup mock storage to return a session with no document state
        mock_storage_service.get_session.return_value = {
            "id": "test-session-id",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T01:00:00",
            "document_type": "EU AI Act Model Card",
            "document_state": {},
            "messages": []
        }
        
        # Send request
        response = test_client.get("/api/documents/test-session-id/export")
        
        # Check response (should be 400 Bad Request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_list_document_templates(self, test_client):
        """Test listing available document templates"""
        # Send request
        response = test_client.get("/api/documents/templates")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), dict)
        assert "EU AI Act Model Card" in response.json()
        assert "US Model Risk Assessment" in response.json()
        assert "General Model Card" in response.json()
    
    def test_get_document_status(self, test_client, mock_storage_service, sample_session_data):
        """Test getting document completion status"""
        # Setup mock storage to return our sample session
        mock_storage_service.get_session.return_value = sample_session_data
        
        # Send request
        response = test_client.get(f"/api/documents/{sample_session_data['id']}/status")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["document_type"] == sample_session_data["document_type"]
        assert "completion_percentage" in response.json()
        assert "completion_status" in response.json()
        
        # Check that storage service was called
        mock_storage_service.get_session.assert_called_with(sample_session_data["id"])
    
    def test_get_document_status_nonexistent_session(self, test_client, mock_storage_service):
        """Test getting document status for a non-existent session"""
        # Setup mock storage to return None (session not found)
        mock_storage_service.get_session.return_value = None
        
        # Send request
        response = test_client.get("/api/documents/nonexistent-session-id/status")
        
        # Check response (should be 404 Not Found)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_document_status_no_document_state(self, test_client, mock_storage_service):
        """Test getting document status for a session with no document state"""
        # Setup mock storage to return a session with no document state
        mock_storage_service.get_session.return_value = {
            "id": "test-session-id",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T01:00:00",
            "document_type": "EU AI Act Model Card",
            "messages": []
        }
        
        # Send request
        response = test_client.get("/api/documents/test-session-id/status")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["completion_percentage"] == 0
        assert response.json()["completion_status"] == {} 