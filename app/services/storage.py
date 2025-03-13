import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from supabase import create_client, Client
from ..config import settings
from ..models.chat import Session, SessionSummary

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        
        if not url or not key:
            logger.warning("Supabase credentials not provided. Using memory storage as fallback.")
            self.supabase = None
            self.memory_storage = {}
        else:
            try:
                self.supabase: Client = create_client(url, key)
                self.memory_storage = None
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.supabase = None
                self.memory_storage = {}
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by ID"""
        if not session_id:
            return None
            
        try:
            if self.supabase:
                response = self.supabase.table("sessions").select("*").eq("id", session_id).execute()
                
                if response.data and len(response.data) > 0:
                    session_data = response.data[0]
                    # Convert string representation of messages and document state back to objects
                    if "messages" in session_data and isinstance(session_data["messages"], str):
                        session_data["messages"] = json.loads(session_data["messages"])
                    if "document_state" in session_data and isinstance(session_data["document_state"], str):
                        session_data["document_state"] = json.loads(session_data["document_state"])
                    return session_data
                return None
            else:
                return self.memory_storage.get(session_id)
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
            return None
            
    async def save_session(self, session_data: Dict[str, Any]) -> str:
        """Save a session and return the session ID"""
        if not session_data:
            raise ValueError("No session data provided")
            
        # Ensure there's an ID
        if "id" not in session_data or not session_data["id"]:
            session_data["id"] = str(uuid.uuid4())
            
        # Update timestamps
        session_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in session_data:
            session_data["created_at"] = session_data["updated_at"]
            
        try:
            if self.supabase:
                # Prepare data for Postgres - convert complex objects to strings
                db_session = session_data.copy()
                if "messages" in db_session and not isinstance(db_session["messages"], str):
                    db_session["messages"] = json.dumps(db_session["messages"])
                if "document_state" in db_session and not isinstance(db_session["document_state"], str):
                    db_session["document_state"] = json.dumps(db_session["document_state"])
                
                # Upsert the session
                self.supabase.table("sessions").upsert(db_session).execute()
            else:
                self.memory_storage[session_data["id"]] = session_data
                
            return session_data["id"]
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            # If we fail to save to Supabase, fallback to memory
            if self.memory_storage is None:
                self.memory_storage = {}
            self.memory_storage[session_data["id"]] = session_data
            return session_data["id"]
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[SessionSummary]:
        """List all sessions, optionally filtered by user ID"""
        try:
            if self.supabase:
                query = self.supabase.table("sessions").select("id, created_at, updated_at, document_type")
                
                if user_id:
                    query = query.eq("user_id", user_id)
                    
                response = query.order("updated_at", desc=True).execute()
                
                if response.data:
                    return [
                        SessionSummary(
                            id=session["id"],
                            created_at=datetime.fromisoformat(session["created_at"]) 
                                if isinstance(session["created_at"], str) else session["created_at"],
                            updated_at=datetime.fromisoformat(session["updated_at"]) 
                                if isinstance(session["updated_at"], str) else session["updated_at"],
                            document_type=session.get("document_type")
                        )
                        for session in response.data
                    ]
                return []
            else:
                # Convert memory storage to session summaries
                return [
                    SessionSummary(
                        id=session_id,
                        created_at=datetime.fromisoformat(session["created_at"]) 
                            if isinstance(session["created_at"], str) else session["created_at"],
                        updated_at=datetime.fromisoformat(session["updated_at"]) 
                            if isinstance(session["updated_at"], str) else session["updated_at"],
                        document_type=session.get("document_type")
                    )
                    for session_id, session in self.memory_storage.items()
                    if not user_id or session.get("user_id") == user_id
                ]
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            return []
            
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID"""
        if not session_id:
            return False
            
        try:
            if self.supabase:
                self.supabase.table("sessions").delete().eq("id", session_id).execute()
            else:
                if session_id in self.memory_storage:
                    del self.memory_storage[session_id]
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False 