"""
Test validation utilities for candidate endpoints.
"""
from fastapi import HTTPException, status
from models.candidate import Candidate


def validate_test_in_progress(candidate: Candidate, resource_name: str = "questions") -> None:
    """
    Validate that the candidate's test is in progress.
    
    Raises HTTPException if test is not in progress with appropriate error message.
    
    Args:
        candidate: Candidate model instance
        resource_name: Name of the resource being accessed (e.g., "questions", "question")
                      Used in error messages for better context.
    
    Raises:
        HTTPException: 403 if test is not in progress
    """
    candidate_status = candidate.status.lower() if candidate.status else None
    
    if candidate_status != 'in progress':
        # Determine verb form based on singular/plural
        verb = "are" if resource_name.endswith('s') else "is"
        
        if candidate_status in ['shortlisted', 'rejected', 'scheduled']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Test has not started yet. The assigned {resource_name} {verb} only available during the test."
            )
        elif candidate_status in ['completed', 'selected', 'not selected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Test has been completed. The assigned {resource_name} {verb} no longer available."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Test is not in progress. The assigned {resource_name} {verb} only available during an active test session."
            )

