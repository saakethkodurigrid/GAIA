"""
System Design API routes for interview-related operations.
"""
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
    ChatHistoryResponse, FinalReportResponse, ProactivePromptResponse
)
import asyncio
import json

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
        SessionResponse with question details
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
        
        # Get question_uuid from request (required)
        if not request.question_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_uuid is required"
            )
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, request.question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.update_canvas(request, current_candidate.candidate_id, request.question_uuid)
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
        request: ChatMessageRequest with message and question_uuid
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ChatMessageResponse with user message and AI response (if applicable)
    """
    try:
        service = SystemDesignService(db)
        
        # Get question_uuid from request (required)
        if not request.question_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_uuid is required"
            )
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, request.question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.send_message(request, current_candidate.candidate_id, request.question_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )


@router.get("/sessions/{session_id}/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get full chat history for a session.
    
    Args:
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ChatHistoryResponse with list of messages
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return service.get_chat_history(current_candidate.candidate_id, question_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat history: {str(e)}"
        )


@router.post("/sessions/{question_uuid}/end", response_model=FinalReportResponse)
async def end_session(
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    End session and generate final report.
    
    Args:
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        FinalReportResponse with evaluation report
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.generate_final_report(current_candidate.candidate_id, question_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ending session: {str(e)}"
        )


@router.get("/sessions/{question_uuid}/report", response_model=FinalReportResponse)
async def get_report(
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get final evaluation report.
    
    Args:
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        FinalReportResponse with evaluation report
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.generate_final_report(current_candidate.candidate_id, question_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching report: {str(e)}"
        )


@router.get("/sessions/{question_uuid}/check-prompts", response_model=ProactivePromptResponse)
async def check_prompts(
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Check if any proactive prompts should be triggered.
    Frontend should poll this endpoint every 5-10 seconds.
    
    Args:
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ProactivePromptResponse with prompt if available
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.check_proactive_prompts(current_candidate.candidate_id, question_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking prompts: {str(e)}"
        )


@router.get("/sessions/{question_uuid}/prompts-stream")
async def prompts_stream(
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events (SSE) stream for proactive prompts.
    Frontend connects once and receives prompts as they're generated.
    More efficient than polling /check-prompts repeatedly.
    
    Args:
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        StreamingResponse with SSE stream
        
    Stream Format:
        data: {"has_prompt": true, "prompt": "Your prompt text here"}
        
        data: {"has_prompt": false}  // Heartbeat
        
        data: {"has_prompt": false, "closed": true}  // Stream closed
        
        data: {"error": "Error message"}  // Error occurred
    """
    try:
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        async def event_stream():
            """Generate SSE stream"""
            try:
                # Timeout after 5 minutes of inactivity
                timeout_start = asyncio.get_event_loop().time()
                timeout_duration = 300  # 5 minutes
                
                while True:
                    # Check if timeout reached
                    elapsed = asyncio.get_event_loop().time() - timeout_start
                    if elapsed > timeout_duration:
                        # Send closure event
                        yield f"data: {json.dumps({'has_prompt': False, 'closed': True})}\n\n"
                        break
                    
                    try:
                        # Check for prompts using the service
                        prompt_response = await service.check_proactive_prompts(
                            current_candidate.candidate_id, 
                            question_uuid
                        )
                        
                        if prompt_response.has_prompt and prompt_response.prompt:
                            # Send prompt event
                            yield f"data: {json.dumps({'has_prompt': True, 'prompt': prompt_response.prompt})}\n\n"
                            # Reset timeout on activity
                            timeout_start = asyncio.get_event_loop().time()
                        else:
                            # Send heartbeat (no prompt available)
                            yield f"data: {json.dumps({'has_prompt': False})}\n\n"
                        
                    except Exception as e:
                        # Send error event
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    
                    # Check every 2.5 seconds
                    await asyncio.sleep(2.5)
                    
            except asyncio.CancelledError:
                # Client disconnected
                pass
            except Exception as e:
                # Unexpected error
                yield f"data: {json.dumps({'error': f'Stream error: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating prompt stream: {str(e)}"
        )

