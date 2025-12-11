"""
System Design API routes for interview-related operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_candidate
from models.candidate import Candidate
from services.system_design_service import SystemDesignService
from schemas.system_design import (
    SessionCreateRequest, SessionResponse,
    ChatMessageRequest, ChatMessageResponse, CanvasUpdateRequest, CanvasUpdateResponse,
    ChatHistoryResponse, FinalReportResponse
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

