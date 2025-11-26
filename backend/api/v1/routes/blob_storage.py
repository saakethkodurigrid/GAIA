"""
Blob Storage API routes for uploading and retrieving candidate images and videos.
"""
import io
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, status, Path, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_candidate
from models.candidate import Candidate
from services.blob_storage_service import BlobStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blob-storage", tags=["Blob Storage"])

# Initialize blob storage service
try:
    blob_service = BlobStorageService()
except Exception as e:
    logger.warning(f"Failed to initialize blob storage service: {e}")
    logger.warning("Make sure AZURE_STORAGE_CONNECTION_STRING is set in .env file")
    blob_service = None


@router.post("/upload/image/{candidate_id}")
async def upload_image(
    candidate_id: str = Path(..., description="Unique candidate identifier", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    file: UploadFile = File(..., description="Image file to upload"),
    current_candidate: Candidate = Depends(get_current_candidate)
):
    """
    Upload a user image associated with a candidate ID.
    
    Only the authenticated candidate can upload their own images.
    
    - **candidate_id**: Unique identifier for the candidate (UUID format)
    - **file**: Image file (jpg, jpeg, png)
    
    Returns:
        dict: Upload result with blob URL and metadata
        
    Raises:
        HTTPException: 
            - 400: If validation fails or upload error
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to upload for another candidate
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only upload your own images."
        )
    
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Blob storage service not initialized"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to blob storage
        result = blob_service.upload_image(
            candidate_id=candidate_id,
            file_content=file_content,
            filename=file.filename or "image"
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Image upload failed for candidate_id {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/upload/video/{candidate_id}")
async def upload_video(
    candidate_id: str = Path(..., description="Unique candidate identifier", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    file: UploadFile = File(..., description="Video file to upload"),
    current_candidate: Candidate = Depends(get_current_candidate)
):
    """
    Upload a user video associated with a candidate ID.
    
    Only the authenticated candidate can upload their own videos.
    
    - **candidate_id**: Unique identifier for the candidate (UUID format)
    - **file**: Video file (mp4, webm)
    
    Returns:
        dict: Upload result with blob URL and metadata
        
    Raises:
        HTTPException: 
            - 400: If validation fails or upload error
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to upload for another candidate
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only upload your own videos."
        )
    
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Blob storage service not initialized"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to blob storage
        result = blob_service.upload_video(
            candidate_id=candidate_id,
            file_content=file_content,
            filename=file.filename or "video"
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Video upload failed for candidate_id {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/fetch/image/{candidate_id}")
async def fetch_image(
    candidate_id: str = Path(..., description="Unique candidate identifier", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate)
):
    """
    Fetch a user image by candidate ID.
    
    Only the authenticated candidate can fetch their own images.
    
    - **candidate_id**: Unique identifier for the candidate (UUID format)
    
    Returns:
        StreamingResponse: Image file stream
        
    Raises:
        HTTPException: 
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to fetch another candidate's image
            - 404: If image not found
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only fetch your own images."
        )
    
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Blob storage service not initialized"
        )
    
    try:
        result = blob_service.get_image(candidate_id)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No image found for candidate ID: {candidate_id}"
            )
        
        content, content_type, filename = result
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image fetch failed for candidate_id {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fetch failed: {str(e)}"
        )


@router.get("/fetch/video/{candidate_id}")
async def fetch_video(
    candidate_id: str = Path(..., description="Unique candidate identifier", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate)
):
    """
    Fetch a user video by candidate ID.
    
    Only the authenticated candidate can fetch their own videos.
    
    - **candidate_id**: Unique identifier for the candidate (UUID format)
    
    Returns:
        StreamingResponse: Video file stream
        
    Raises:
        HTTPException: 
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to fetch another candidate's video
            - 404: If video not found
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only fetch your own videos."
        )
    
    if not blob_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Blob storage service not initialized"
        )
    
    try:
        result = blob_service.get_video(candidate_id)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No video found for candidate ID: {candidate_id}"
            )
        
        content, content_type, filename = result
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video fetch failed for candidate_id {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fetch failed: {str(e)}"
        )

