from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..models.chat import MessageRequest, MessageResponse, Message, Session
from ..services.llm import LLMService
from ..services.storage import StorageService
from ..services.n8n import N8nService

router = APIRouter(prefix="/chat")
logger = logging.getLogger(__name__)

# Service dependencies
def get_llm_service():
    return LLMService()

def get_storage_service():
    return StorageService()
    
def get_n8n_service():
    return N8nService()

@router.post("/message", response_model=MessageResponse)
async def process_message(
    request: MessageRequest,
    llm_service: LLMService = Depends(get_llm_service),
    storage_service: StorageService = Depends(get_storage_service),
    n8n_service: N8nService = Depends(get_n8n_service)
):
    """
    Process a user message and generate an AI response with document updates
    """
    try:
        # Get or create session
        session_data = None
        if request.session_id:
            session_data = await storage_service.get_session(request.session_id)
            
            if not session_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session with ID {request.session_id} not found"
                )
        else:
            # Create a new session
            session_data = {
                "id": None,  # Will be set by storage service
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": [],
                "document_state": {},
                "document_type": None
            }
                
        # Add user message to history
        user_message = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        }
        session_data["messages"].append(user_message)
        
        # Convert message history to format expected by LLM service
        message_history = session_data["messages"]
        
        # Analyze the message with LLM
        intent, entities = await llm_service.analyze_message(
            request.message, 
            message_history
        )
        
        # Initialize document_update
        document_update = {}
        ai_response = ""
        
        # Process based on intent
        if intent == "select_document_type":
            # Create a new document state based on selected type
            document_type = entities.get("document_type", "EU AI Act Model Card")
            
            # Initialize document state with basic structure
            session_data["document_type"] = document_type
            session_data["document_state"] = {
                "type": document_type,
                "data": {},
                "completion_status": {}
            }
            
            # Generate response confirming document type selection
            ai_response = await llm_service.generate_response(
                intent, 
                entities, 
                session_data["document_state"]
            )
            
            document_update = session_data["document_state"]
            
        elif intent == "connect_repository":
            # Extract repository URL from entities
            repo_url = entities.get("repository_url", "")
            if not repo_url:
                # If no repository URL found, try to extract it from the message
                # This is a fallback in case intent analysis doesn't extract it correctly
                words = request.message.split()
                for word in words:
                    if word.startswith("https://github.com/") or word.startswith("http://github.com/"):
                        repo_url = word
                        break
            
            if repo_url:
                # Trigger n8n workflow to analyze repository
                repo_data = await n8n_service.analyze_repository(repo_url)
                
                if repo_data:
                    # Update document state with repository information
                    if "document_state" not in session_data or not session_data["document_state"]:
                        session_data["document_state"] = {
                            "type": session_data.get("document_type", "EU AI Act Model Card"),
                            "data": {},
                            "completion_status": {}
                        }
                    
                    # Update model details if available
                    if "model_name" in repo_data:
                        if "model_details" not in session_data["document_state"]["data"]:
                            session_data["document_state"]["data"]["model_details"] = {}
                        
                        model_details = session_data["document_state"]["data"]["model_details"]
                        model_details["name"] = repo_data.get("model_name")
                        model_details["version"] = repo_data.get("model_version")
                        model_details["description"] = repo_data.get("model_description")
                        model_details["framework"] = repo_data.get("model_framework")
                        model_details["license"] = repo_data.get("model_license")
                        
                        # Mark model details as complete in completion status
                        session_data["document_state"]["completion_status"]["model_details"] = True
                    
                    # Update technical specifications if available
                    if "model_inputs" in repo_data or "model_outputs" in repo_data or "dependencies" in repo_data:
                        if "technical_specifications" not in session_data["document_state"]["data"]:
                            session_data["document_state"]["data"]["technical_specifications"] = {}
                        
                        tech_specs = session_data["document_state"]["data"]["technical_specifications"]
                        
                        if "model_inputs" in repo_data:
                            tech_specs["input_format"] = ", ".join(repo_data["model_inputs"])
                        
                        if "model_outputs" in repo_data:
                            tech_specs["output_format"] = ", ".join(repo_data["model_outputs"])
                        
                        if "dependencies" in repo_data:
                            tech_specs["dependencies"] = repo_data["dependencies"]
                    
                    document_update = session_data["document_state"]
                    
                    # Generate response about findings from repository
                    ai_response = f"I've analyzed the repository at {repo_url} and extracted information for your model card. "
                    if "model_name" in repo_data:
                        ai_response += f"I found that your model is called '{repo_data['model_name']}'"
                        if "model_version" in repo_data:
                            ai_response += f" (version {repo_data['model_version']})"
                        ai_response += ". "
                    
                    # Ask about additional information
                    next_question = await llm_service.determine_next_question(session_data["document_state"])
                    ai_response += f"\n\n{next_question}"
                else:
                    ai_response = f"I tried to analyze the repository at {repo_url}, but couldn't extract the necessary information. Could you please provide more details about your model manually?"
            else:
                ai_response = "I understand you want to connect a GitHub repository. Please provide the URL to your repository so I can analyze it."
        
        elif intent == "provide_information":
            # Update document state with provided information
            if "document_state" not in session_data or not session_data["document_state"]:
                # If no document state exists, create one
                if not session_data.get("document_type"):
                    session_data["document_type"] = "EU AI Act Model Card"
                
                session_data["document_state"] = {
                    "type": session_data["document_type"],
                    "data": {},
                    "completion_status": {}
                }
            
            # Extract field information from entities
            # This is a simplified version; in a production system, you would
            # have more sophisticated entity mapping and validation
            for field, value in entities.items():
                if field == "intent":
                    continue
                
                # Map field to document section (simplified)
                if field.startswith("model_"):
                    section = "model_details"
                    subfield = field
                elif field.startswith("use_") or field == "primary_purpose" or field == "intended_users":
                    section = "intended_use"
                    subfield = field
                elif field.startswith("risk_"):
                    section = "risk_assessment"
                    subfield = field
                elif field.startswith("performance_") or field.startswith("metric_"):
                    section = "performance_metrics"
                    subfield = field
                elif field.startswith("data_") or field.startswith("training_"):
                    section = "training_data"
                    subfield = field
                elif field.startswith("tech_") or field.startswith("input_") or field.startswith("output_"):
                    section = "technical_specifications"
                    subfield = field
                elif field.startswith("oversight_") or field.startswith("human_"):
                    section = "human_oversight"
                    subfield = field
                elif field.startswith("compliance_") or field.startswith("standard_"):
                    section = "compliance_information"
                    subfield = field
                elif field.startswith("contact_") or field.startswith("developer_"):
                    section = "contact_information"
                    subfield = field
                else:
                    # Default to a general section
                    section = "additional_information"
                    subfield = field
                
                # Ensure section exists
                if section not in session_data["document_state"]["data"]:
                    session_data["document_state"]["data"][section] = {}
                
                # Update field
                session_data["document_state"]["data"][section][subfield] = value
                
                # Update completion status
                session_data["document_state"]["completion_status"][section] = True
            
            document_update = session_data["document_state"]
            
            # Calculate document completion
            completion_percentage = 0
            if session_data["document_state"]["completion_status"]:
                completed = sum(1 for status in session_data["document_state"]["completion_status"].values() if status)
                total = len(session_data["document_state"]["completion_status"])
                completion_percentage = (completed / total) * 100 if total > 0 else 0
            
            # Determine next question based on what's missing
            next_question = await llm_service.determine_next_question(session_data["document_state"])
            
            # Generate response
            ai_response = await llm_service.generate_response(
                intent, 
                entities, 
                session_data["document_state"]
            )
            
            # Add next question if we have one
            if next_question:
                ai_response += f"\n\n{next_question}"
        
        elif intent == "request_export":
            # Check if document is complete enough for export
            completion_percentage = 0
            if session_data.get("document_state") and session_data["document_state"].get("completion_status"):
                completed = sum(1 for status in session_data["document_state"]["completion_status"].values() if status)
                total = len(session_data["document_state"]["completion_status"])
                completion_percentage = (completed / total) * 100 if total > 0 else 0
            
            if completion_percentage >= 70:  # At least 70% complete to allow export
                ai_response = f"Your document is {completion_percentage:.1f}% complete and ready for export. You can download it using the export button or API endpoint."
            else:
                # Generate response with missing fields
                ai_response = await llm_service.generate_response(
                    intent, 
                    entities, 
                    session_data["document_state"]
                )
        
        else:  # general_query
            # Generate a general response
            ai_response = await llm_service.generate_response(
                "general_query", 
                {"query": request.message}, 
                session_data.get("document_state", {})
            )
        
        # Add assistant message to history
        assistant_message = {
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        session_data["messages"].append(assistant_message)
        
        # Update session timestamp
        session_data["updated_at"] = datetime.now().isoformat()
        
        # Save updated session
        session_id = await storage_service.save_session(session_data)
        
        # Return response
        return MessageResponse(
            message=ai_response,
            document_update=document_update,
            session_id=session_id
        )
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        ) 