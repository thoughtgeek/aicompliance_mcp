import os
import json
import requests
import logging
from typing import List, Dict, Any, Tuple, Optional
from ..config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_url = "https://api-inference.huggingface.co/models/"
        self.model = settings.HF_MODEL
        self.api_key = settings.HF_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("No Hugging Face API key provided. LLM functionality will be limited.")
    
    async def analyze_message(self, message: str, history: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """Determine the intent and extract entities from a message."""
        
        # Create system prompt for intent classification
        system_prompt = """
        You analyze user messages to identify intent and extract entities.
        Return a JSON object with "intent" and "entities".
        
        Intents:
        - select_document_type: User wants to create a specific document
        - connect_repository: User wants to connect a GitHub repository
        - provide_information: User is providing information for a field
        - request_export: User wants to export the document
        - general_query: General conversation
        
        Entities should be field names and values, or repository URLs.
        """
        
        # Format conversation history for the prompt
        formatted_history = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in history[-5:]  # Include only last 5 messages for context
        ])
        
        # Create complete prompt
        full_prompt = f"""
        {system_prompt}
        
        Conversation history:
        {formatted_history}
        
        Current message: {message}
        
        Analyze the intent and entities from the current message and return a JSON object.
        """
        
        try:
            # Make API request to Hugging Face
            response = await self._call_huggingface(full_prompt)
            
            # Parse the response to extract intent and entities
            parsed_response = self._parse_llm_response(response)
            intent = parsed_response.get("intent", "general_query")
            entities = parsed_response.get("entities", {})
            
            return intent, entities
            
        except Exception as e:
            logger.error(f"Error analyzing message: {str(e)}")
            # Return a fallback intent if analysis fails
            return "general_query", {}
    
    async def determine_next_question(self, document_state: Dict[str, Any]) -> str:
        """Determine what information to ask for next based on missing fields."""
        # Format the prompt to check document state
        prompt = f"""
        Given a partially completed document, determine what information to ask next.
        
        Document state:
        {json.dumps(document_state, indent=2)}
        
        What's the most important missing field to ask about next? Provide a natural-sounding question
        to request this information from the user.
        """
        
        try:
            response = await self._call_huggingface(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Error determining next question: {str(e)}")
            return "Can you provide more information about the model?"
    
    async def generate_response(self, intent: str, entities: Dict[str, Any], 
                               document_state: Dict[str, Any], 
                               document_templates: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response based on intent, entities, and document state."""
        
        # Create a prompt based on the intent
        prompt = ""
        
        if intent == "select_document_type":
            template_descriptions = ""
            if document_templates:
                for template_type, template in document_templates.items():
                    template_descriptions += f"- {template_type}: {template.get('description', '')}\n"
            
            prompt = f"""
            The user wants to create a document of type: {entities.get('document_type', 'unspecified')}
            
            Available templates:
            {template_descriptions}
            
            Generate a helpful response confirming the document type selection and explaining what
            information will be needed. If the requested document type is not available, suggest
            alternatives.
            """
            
        elif intent == "connect_repository":
            repo_url = entities.get("repository_url", "")
            prompt = f"""
            The user wants to connect to a repository: {repo_url}
            
            Generate a helpful response acknowledging this and explaining what information
            will be extracted from the repository. If no repository URL was provided,
            ask the user to provide one.
            """
            
        elif intent == "provide_information":
            prompt = f"""
            The user is providing information for their document:
            {json.dumps(entities, indent=2)}
            
            Current document state:
            {json.dumps(document_state, indent=2)}
            
            Generate a helpful response acknowledging the information provided.
            Suggest what information might be needed next, or confirm if all required
            information has been collected.
            """
            
        elif intent == "request_export":
            completion = self._calculate_completion(document_state)
            prompt = f"""
            The user wants to export their document.
            
            Current document completion: {completion}%
            
            Generate a helpful response. If the document is not complete, explain what
            information is still needed. If it's complete, confirm that the document
            will be exported.
            """
            
        else:  # general_query
            prompt = f"""
            The user has a general query: {entities.get('query', '')}
            
            Generate a helpful response to answer their question about the document generation
            process. Be concise but informative.
            """
            
        try:
            return await self._call_huggingface(prompt)
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later."
    
    async def _call_huggingface(self, prompt: str) -> str:
        """Make a call to the Hugging Face Inference API."""
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "do_sample": True
                }
            }
            
            response = requests.post(
                f"{self.api_url}{self.model}",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Hugging Face API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")
                
            result = response.json()
            
            # Extract text from different model response formats
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"]
                return result[0]
            elif isinstance(result, dict) and "generated_text" in result:
                return result["generated_text"]
            elif isinstance(result, str):
                return result
            else:
                logger.error(f"Unexpected response format: {result}")
                return str(result)
                
        except Exception as e:
            logger.error(f"Error calling Hugging Face API: {str(e)}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response to extract structured data."""
        try:
            # Try to find JSON in the response
            start_idx = response.find("{")
            end_idx = response.rfind("}")
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx+1]
                return json.loads(json_str)
            else:
                # If no JSON found, try to extract intent from text
                response_lower = response.lower()
                
                if "document type" in response_lower or "create" in response_lower:
                    return {"intent": "select_document_type", "entities": {}}
                elif "repository" in response_lower or "github" in response_lower:
                    return {"intent": "connect_repository", "entities": {}}
                elif "export" in response_lower or "generate" in response_lower:
                    return {"intent": "request_export", "entities": {}}
                else:
                    return {"intent": "provide_information", "entities": {}}
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {"intent": "general_query", "entities": {}}
    
    def _calculate_completion(self, document_state: Dict[str, Any]) -> float:
        """Calculate document completion percentage."""
        if not document_state or "completion_status" not in document_state:
            return 0.0
            
        completion_status = document_state["completion_status"]
        if not completion_status:
            return 0.0
            
        completed = sum(1 for status in completion_status.values() if status)
        total = len(completion_status)
        
        return round((completed / total) * 100, 1) if total > 0 else 0.0 