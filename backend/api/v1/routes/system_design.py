"""
System Design API routes for interview-related operations.
"""
import asyncio
import json
import time
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_candidate
from models.candidate import Candidate
from services.system_design_service import SystemDesignService
from schemas.system_design import (
    SessionCreateRequest, SessionResponse,
    ChatMessageRequest, ChatMessageResponse, CanvasUpdateRequest, CanvasUpdateResponse,
    ProactivePromptResponse, ChatHistoryResponse, FinalReportResponse
)

router = APIRouter(prefix="/system-design", tags=["System Design"])


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Create a new interview session.
    
    Args:
        request: SessionCreateRequest with question details
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        SessionResponse with session_id and question details
    """
    try:
        # Ensure candidate_id in request matches authenticated candidate (or auto-fill)
        if request.candidate_id and request.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidate ID mismatch"
            )
        
        # Auto-fill candidate_id from authenticated user
        request.candidate_id = current_candidate.candidate_id
        
        service = SystemDesignService(db)
        return service.create_session(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


@router.post("/canvas/update", response_model=CanvasUpdateResponse)
async def update_canvas(
    request: CanvasUpdateRequest,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Handle canvas updates (save, submit, or update).
    
    Args:
        request: CanvasUpdateRequest with canvas data and action
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        CanvasUpdateResponse with status and evaluation (if submitted)
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session belongs to candidate
        session = service.get_session(request.session_id, current_candidate.candidate_id)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.update_canvas(request, current_candidate.candidate_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating canvas: {str(e)}"
        )


@router.post("/chat/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Send a chat message.
    
    Args:
        request: ChatMessageRequest with message and session_id
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ChatMessageResponse with user message and AI response (if applicable)
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session belongs to candidate
        session = service.get_session(request.session_id, current_candidate.candidate_id)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.send_message(request, current_candidate.candidate_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )


@router.get("/sessions/{session_id}/check-prompts", response_model=ProactivePromptResponse)
async def check_proactive_prompts(
    session_id: str = Path(..., description="Session ID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Check if any proactive prompts should be triggered.
    Frontend should poll this endpoint periodically (every 5-10 seconds).
    Consider using /prompts-stream endpoint for better performance.
    
    Args:
        session_id: Session ID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ProactivePromptResponse with prompt if available
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session belongs to candidate
        session = service.get_session(session_id, current_candidate.candidate_id)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.check_proactive_prompts(session_id, current_candidate.candidate_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking prompts: {str(e)}"
        )


@router.get("/sessions/{session_id}/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Path(..., description="Session ID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get full chat history for a session.
    
    Args:
        session_id: Session ID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ChatHistoryResponse with list of messages
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session belongs to candidate
        session = service.get_session(session_id, current_candidate.candidate_id)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return service.get_chat_history(session_id, current_candidate.candidate_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat history: {str(e)}"
        )


@router.post("/sessions/{session_id}/end", response_model=FinalReportResponse)
async def end_session(
    session_id: str = Path(..., description="Session ID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    End session and generate final report.
    
    Args:
        session_id: Session ID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        FinalReportResponse with evaluation report
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session belongs to candidate
        session = service.get_session(session_id, current_candidate.candidate_id)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.generate_final_report(session_id, current_candidate.candidate_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ending session: {str(e)}"
        )


@router.get("/sessions/{session_id}/report", response_model=FinalReportResponse)
async def get_report(
    session_id: str = Path(..., description="Session ID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get final evaluation report.
    
    Args:
        session_id: Session ID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        FinalReportResponse with evaluation report
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session belongs to candidate
        session = service.get_session(session_id, current_candidate.candidate_id)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.generate_final_report(session_id, current_candidate.candidate_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching report: {str(e)}"
        )


@router.get("/sessions/{session_id}/prompts-stream")
async def stream_proactive_prompts(
    session_id: str = Path(..., description="Session ID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events stream for proactive prompts.
    Frontend connects once and receives prompts as they're generated.
    This is more efficient than polling /check-prompts repeatedly.
    
    Args:
        session_id: Session ID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        StreamingResponse with SSE events containing prompts
    """
    service = SystemDesignService(db)
    
    # Verify session ownership
    session = service.get_session(session_id, current_candidate.candidate_id)
    if session.candidate_id != current_candidate.candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Session does not belong to this candidate."
        )
    
    async def event_generator():
        last_prompt = None
        
        try:
            while True:
                # Check for new prompts every 1 second for faster response
                await asyncio.sleep(1)
                
                # Only check if enough time has passed since last activity
                current_time = time.time()
                if session.last_activity_time and (current_time - session.last_activity_time) > 300:
                    # No activity for 5 minutes, stop checking
                    yield f"data: {json.dumps({'has_prompt': False, 'closed': True})}\n\n"
                    break
                
                prompt_response = await service.check_proactive_prompts(session_id, current_candidate.candidate_id)
                
                # Only send if prompt is new and different
                if prompt_response.has_prompt and prompt_response.prompt and prompt_response.prompt != last_prompt:
                    last_prompt = prompt_response.prompt
                    yield f"data: {json.dumps({'has_prompt': True, 'prompt': prompt_response.prompt})}\n\n"
                else:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'has_prompt': False})}\n\n"
                    
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

