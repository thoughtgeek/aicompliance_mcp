from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from ..models.chat import Session, SessionSummary
from ..services.storage import StorageService

router = APIRouter(prefix="/sessions")
logger = logging.getLogger(__name__)

# Service dependencies
def get_storage_service():
    return StorageService()

@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Get a specific session by ID
    """
    try:
        session_data = await storage_service.get_session(session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
            
        return session_data
        
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session: {str(e)}"
        )

@router.get("/", response_model=List[SessionSummary])
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter sessions by user ID"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    List all sessions, optionally filtered by user ID
    """
    try:
        sessions = await storage_service.list_sessions(user_id)
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing sessions: {str(e)}"
        )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Delete a session by ID
    """
    try:
        success = await storage_service.delete_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found or could not be deleted"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        ) 