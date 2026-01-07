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
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system-design", tags=["System Design"])


@router.post("/{candidate_id}/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    candidate_id: str = Path(..., description="Candidate UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Create a new interview session.
    
    Args:
        candidate_id: Candidate UUID (from path)
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


@router.post("/{candidate_id}/canvas/update", response_model=CanvasUpdateResponse)
async def update_canvas(
    request: CanvasUpdateRequest,
    candidate_id: str = Path(..., description="Candidate UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Handle canvas updates (save, submit, or update).
    
    Args:
        candidate_id: Candidate UUID (from path)
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
        
        # Normalize UUID by stripping trailing spaces
        question_uuid = request.question_uuid.strip()
        
        # DEBUG: Log canvas update details
        elements_count = len(request.canvas_data.elements) if request.canvas_data else 0
        logger.info(f"[CANVAS UPDATE] Candidate: {candidate_id[:8]}..., Question: {question_uuid}, Action: {request.action}, Elements: {elements_count}")
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.update_canvas(request, current_candidate.candidate_id, question_uuid)
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


@router.post("/{candidate_id}/chat/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    candidate_id: str = Path(..., description="Candidate UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Send a chat message.
    
    Args:
        candidate_id: Candidate UUID (from path)
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
        
        # Normalize UUID by stripping trailing spaces
        question_uuid = request.question_uuid.strip()
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        return await service.send_message(request, current_candidate.candidate_id, question_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )


@router.get("/{candidate_id}/sessions/{question_uuid}/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(
    candidate_id: str = Path(..., description="Candidate UUID"),
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get full chat history for a session.
    
    Args:
        candidate_id: Candidate UUID (from path)
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ChatHistoryResponse with list of messages
    """
    try:
        # Normalize UUID by stripping trailing spaces
        question_uuid = question_uuid.strip()
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


@router.get("/{candidate_id}/sessions/{question_uuid}/canvas")
async def get_canvas_data(
    candidate_id: str = Path(..., description="Candidate UUID"),
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get current canvas data for a session (loads from Redis for freshest data).
    
    Args:
        candidate_id: Candidate UUID (from path)
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        Canvas data with elements, appState, and files
    """
    try:
        # Normalize UUID by stripping trailing spaces
        question_uuid = question_uuid.strip()
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        # Get canvas data from Redis (freshest source)
        canvas_data = service.get_canvas_data(current_candidate.candidate_id, question_uuid)
        
        return {
            "success": True,
            "canvas": canvas_data,
            "question_uuid": question_uuid
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching canvas data: {str(e)}"
        )


@router.post("/{candidate_id}/sessions/{question_uuid}/end")
async def end_session(
    candidate_id: str = Path(..., description="Candidate UUID"),
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    End session with immediate canvas evaluation, then enqueue full analysis to background.
    
    This endpoint:
    1. Performs immediate canvas evaluation (if canvas exists) - returns quickly
    2. Enqueues full section analysis in background thread (non-blocking)
    
    Args:
        candidate_id: Candidate UUID (from path)
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        Response with immediate evaluation (if available) and status
    """
    try:
        # Normalize UUID by stripping trailing spaces
        question_uuid = question_uuid.strip()
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        # === STEP 1: Immediate Canvas Evaluation (if canvas exists) ===
        immediate_evaluation = None
        if session.current_canvas:
            try:
                logger.info(f"[END_SESSION] Performing immediate canvas evaluation for candidate {candidate_id}")
                
                # Get canvas data
                canvas_json = session.current_canvas
                
                # Get chat context (last 30 messages)
                chat_text = ""
                if session.chat_history:
                    if len(session.chat_history) <= 30:
                        latest_chat = session.chat_history
                    else:
                        latest_chat = session.chat_history[-30:]
                    chat_lines = []
                    for msg in latest_chat:
                        role_label = "Candidate" if msg.role == "user" else "Interviewer"
                        chat_lines.append(f"{role_label}: {msg.content}")
                    chat_text = "\n".join(chat_lines)
                
                # Fetch evaluation criteria
                evaluation_criteria = None
                evaluation_context = None
                if session.question_id:
                    question_metadata = service._get_question_metadata(session.question_id)
                    if question_metadata:
                        evaluation_criteria = question_metadata.get("evaluation_criteria")
                        evaluation_context = question_metadata.get("evaluation_context")
                
                # Perform evaluation
                evaluation = await service.evaluator.evaluate(
                    canvas_json=canvas_json,
                    chat_text=chat_text,
                    question_text=session.question_text,
                    evaluation_criteria=evaluation_criteria,
                    evaluation_context=evaluation_context
                )
                
                # Save evaluation to session
                from utils.system_design.models import Evaluation as EvaluationModel
                eval_obj = EvaluationModel(
                    version=len(session.canvas_versions) + 1,
                    scores=evaluation["scores"],
                    feedback=evaluation["feedback"],
                    follow_up=evaluation.get("follow_up")
                )
                session.evaluations.append(eval_obj)
                
                # Save to Redis (immediate)
                service._save_session_to_redis(candidate_id, question_uuid, session)
                
                # Save to PostgreSQL
                from models.interview_system_design import InterviewSystemDesign
                interview_record = db.query(InterviewSystemDesign).filter(
                    InterviewSystemDesign.candidate_id == candidate_id,
                    InterviewSystemDesign.question_uuid == question_uuid
                ).first()
                
                if interview_record:
                    avg_score = sum(evaluation["scores"].values()) / len(evaluation["scores"]) if evaluation["scores"] else 0
                    if avg_score <= 2.5:
                        final_score = int(round(avg_score * 15))
                    elif avg_score <= 3.5:
                        final_score = int(round(avg_score * 20))
                    else:
                        final_score = int(round(avg_score * 20))
                    
                    interview_record.final_diagram = canvas_json
                    interview_record.final_score = final_score
                    db.commit()
                
                immediate_evaluation = {
                    "scores": evaluation.get("scores", {}),
                    "feedback": evaluation.get("feedback", ""),
                    "follow_up": evaluation.get("follow_up", "")
                }
                
                logger.info(f"[END_SESSION] ✅ Immediate canvas evaluation completed for candidate {candidate_id}")
                
            except Exception as eval_error:
                logger.warning(f"[END_SESSION] Failed immediate canvas evaluation: {str(eval_error)}")
                # Continue - immediate evaluation is nice-to-have, not critical
        
        # === STEP 2: Track Analysis Status ===
        try:
            from services.analysis_status_service import AnalysisStatusService
            from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
            
            status_service = AnalysisStatusService(db)
            current_status = status_service.get_status(candidate_id, SectionType.SYSTEM_DESIGN)
            
            if current_status is None or current_status.status == AnalysisStatusEnum.NOT_STARTED.value:
                status_service.mark_in_progress(candidate_id, SectionType.SYSTEM_DESIGN)
                logger.info(f"[ANALYSIS_STATUS] System Design analysis transitioned to IN_PROGRESS for candidate {candidate_id}")
        except Exception as status_error:
            logger.warning(f"Failed to update analysis status for System Design: {str(status_error)}")
        
        # === STEP 3: Enqueue Full Analysis to Background ===
        import threading
        
        def run_system_design_analysis_async():
            """Helper function to run System Design analysis in background thread."""
            try:
                from core.database import SessionLocal
                background_db = SessionLocal()
                try:
                    from services.section_analysis_service import analyze_system_design
                    analyze_system_design(candidate_id, background_db)
                finally:
                    background_db.close()
            except Exception as e:
                logger.error(f"Error in background System Design analysis thread for candidate {candidate_id}: {str(e)}", exc_info=True)
        
        try:
            analysis_thread = threading.Thread(target=run_system_design_analysis_async, daemon=True)
            analysis_thread.start()
            logger.info(f"[BACKGROUND_ANALYSIS] Enqueued System Design analysis for candidate {candidate_id}")
        except Exception as e:
            logger.warning(f"Failed to enqueue System Design analysis for candidate {candidate_id}: {str(e)}")
        
        # Return response with immediate evaluation (if available)
        response = {
            "success": True,
            "message": "Session ended successfully.",
            "status": "completed"
        }
        
        if immediate_evaluation:
            response["evaluation"] = immediate_evaluation
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ending session: {str(e)}"
        )


@router.get("/{candidate_id}/sessions/{question_uuid}/report")
async def get_report(
    candidate_id: str = Path(..., description="Candidate UUID"),
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get final evaluation report or analysis status.
    
    Returns the report if analysis is completed, or status if still in progress.
    
    Args:
        candidate_id: Candidate UUID (from path)
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        Report if completed, or status information if in progress/not started
    """
    try:
        # Normalize UUID by stripping trailing spaces
        question_uuid = question_uuid.strip()
        service = SystemDesignService(db)
        
        # Verify session exists and belongs to candidate
        session = service.get_session(current_candidate.candidate_id, question_uuid)
        if session.candidate_id != current_candidate.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Session does not belong to this candidate."
            )
        
        # Check analysis status
        try:
            from services.analysis_status_service import AnalysisStatusService
            from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
            from models.interview_analysis_table import InterviewAnalysisTable
            
            status_service = AnalysisStatusService(db)
            current_status = status_service.get_status(candidate_id, SectionType.SYSTEM_DESIGN)
            
            # If COMPLETED, return the analysis from interview_analysis_table
            if current_status and current_status.status == AnalysisStatusEnum.COMPLETED.value:
                # Fetch the analysis from interview_analysis_table
                interview_analysis = db.query(InterviewAnalysisTable).filter(
                    InterviewAnalysisTable.candidate_id == candidate_id
                ).first()
                
                if interview_analysis and interview_analysis.system_design_analysis:
                    analysis = interview_analysis.system_design_analysis
                    return {
                        "success": True,
                        "status": "completed",
                        "score": analysis.get("score", 0),
                        "summary": analysis.get("summary", ""),
                        "key_strengths": analysis.get("key_strengths", []),
                        "things_to_improve": analysis.get("things_to_improve", []),
                        "areas_covered": analysis.get("areas_covered", []),
                        "areas_missed": analysis.get("areas_missed", [])
                    }
            
            # If IN_PROGRESS, return status
            if current_status and current_status.status == AnalysisStatusEnum.IN_PROGRESS.value:
                return {
                    "success": True,
                    "status": "in_progress",
                    "message": "Analysis is being generated. Please check back in a few seconds."
                }
            
            # If NOT_STARTED or FAILED, trigger analysis and return status
            return {
                "success": True,
                "status": "not_started",
                "message": "Analysis has not been started yet. Please end the session first."
            }
            
        except Exception as status_error:
            logger.error(f"Error checking System Design analysis status: {str(status_error)}", exc_info=True)
            # Fallback: try to generate report synchronously
            return await service.generate_final_report(current_candidate.candidate_id, question_uuid)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching report: {str(e)}"
        )


@router.get("/{candidate_id}/sessions/{question_uuid}/check-prompts", response_model=ProactivePromptResponse)
async def check_prompts(
    candidate_id: str = Path(..., description="Candidate UUID"),
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Check if any proactive prompts should be triggered.
    Frontend should poll this endpoint every 5-10 seconds.
    
    Args:
        candidate_id: Candidate UUID (from path)
        question_uuid: Question UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ProactivePromptResponse with prompt if available
    """
    try:
        # Normalize UUID by stripping trailing spaces
        question_uuid = question_uuid.strip()
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


@router.get("/{candidate_id}/sessions/{question_uuid}/prompts-stream")
async def prompts_stream(
    candidate_id: str = Path(..., description="Candidate UUID"),
    question_uuid: str = Path(..., description="Question UUID"),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events (SSE) stream for proactive prompts.
    Frontend connects once and receives prompts as they're generated.
    More efficient than polling /check-prompts repeatedly.
    
    Args:
        candidate_id: Candidate UUID (from path)
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
        # Normalize UUID by stripping trailing spaces
        question_uuid = question_uuid.strip()
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

