import logging
import aiohttp
import json
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger(__name__)

class N8nService:
    def __init__(self):
        self.webhook_url = settings.N8N_GITHUB_WEBHOOK
        
        if not self.webhook_url:
            logger.warning("n8n webhook URL not provided. Repository analysis will be disabled.")
            
    async def analyze_repository(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Trigger an n8n workflow to analyze a GitHub repository.
        
        Args:
            repo_url: The GitHub repository URL to analyze
            
        Returns:
            A dictionary containing the extracted information or None if the operation failed
        """
        if not self.webhook_url:
            logger.error("Cannot analyze repository: n8n webhook URL not configured")
            return None
            
        if not repo_url:
            logger.error("Cannot analyze repository: No repository URL provided")
            return None
            
        try:
            # Prepare payload for n8n webhook
            payload = {
                "repository_url": repo_url,
                "analysis_type": "model_card",
                "callback_url": None  # Could be used for asynchronous processing
            }
            
            # Call the n8n webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        logger.error(f"n8n webhook error: {response.status} - {await response.text()}")
                        return None
                        
                    # Parse response from n8n
                    result = await response.json()
                    
                    # Transform n8n response to document fields
                    return self._transform_repository_data(result)
        
        except Exception as e:
            logger.error(f"Error calling n8n webhook: {str(e)}")
            return None
            
    def _transform_repository_data(self, n8n_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the raw data from n8n to document fields.
        
        Args:
            n8n_data: The raw data returned from the n8n workflow
            
        Returns:
            A dictionary with transformed data ready to be used in document fields
        """
        try:
            # Extract relevant data from n8n response
            # This will depend on what data the n8n workflow returns
            transformed_data = {}
            
            # Basic repository metadata
            if "repository" in n8n_data:
                repo_info = n8n_data["repository"]
                transformed_data["repository_name"] = repo_info.get("name")
                transformed_data["repository_owner"] = repo_info.get("owner", {}).get("login")
                transformed_data["repository_description"] = repo_info.get("description")
                transformed_data["repository_url"] = repo_info.get("html_url")
                
            # Model information (if n8n extracted it)
            if "model_info" in n8n_data:
                model_info = n8n_data["model_info"]
                transformed_data["model_name"] = model_info.get("name")
                transformed_data["model_version"] = model_info.get("version")
                transformed_data["model_description"] = model_info.get("description")
                transformed_data["model_framework"] = model_info.get("framework")
                transformed_data["model_license"] = model_info.get("license")
                
            # Documentation information
            if "documentation" in n8n_data:
                doc_info = n8n_data["documentation"]
                transformed_data["documentation_files"] = doc_info.get("files", [])
                transformed_data["documentation_summary"] = doc_info.get("summary")
                
            # Code analysis (if n8n performed it)
            if "code_analysis" in n8n_data:
                code_analysis = n8n_data["code_analysis"]
                transformed_data["model_inputs"] = code_analysis.get("inputs", [])
                transformed_data["model_outputs"] = code_analysis.get("outputs", [])
                transformed_data["dependencies"] = code_analysis.get("dependencies", [])
                
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming repository data: {str(e)}")
            return {} 