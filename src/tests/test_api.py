import unittest
import requests
from unittest.mock import patch, MagicMock

class TestAPIGateway(unittest.TestCase):
    
    @patch('requests.get')
    def test_health_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response
        
        response = requests.get("http://localhost:8000/health")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})
        
    @patch('requests.post')
    def test_compliance_query(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "risk_category": "high",
            "requirements": ["documentation", "human_oversight", "risk_assessment"],
            "sources": ["Article 6", "Article 9", "Article 14"]
        }
        mock_post.return_value = mock_response
        
        payload = {
            "system_description": "An AI system for automated resume screening",
            "application_domain": "employment",
            "capabilities": ["candidate_ranking"],
            "data_sources": ["resumes"]
        }
        
        response = requests.post("http://localhost:8000/compliance_query", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue("risk_category" in response.json())
        self.assertTrue("requirements" in response.json())
        self.assertTrue("sources" in response.json())

if __name__ == "__main__":
    unittest.main() 