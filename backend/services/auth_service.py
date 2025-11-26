"""
Authentication service with Google OAuth and business logic.
Handles user authentication, authorization, and routing based on user type and status.
"""
import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict
from models.recruiter_admin import RecruiterAdmin
from models.candidate import Candidate
from core.security import GoogleOAuth
from core.config import settings
from schemas.auth import AuthResponse, UserType, CandidateStatus, ErrorResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service class."""
    
    def __init__(self, db: Session):
        """Initialize auth service with database session."""
        self.db = db
        self.google_oauth = GoogleOAuth()
    
    def _extract_domain(self, email: str) -> str:
        """
        Extract domain from email address.
        
        Args:
            email: Email address
            
        Returns:
            Domain name (e.g., 'griddynamics.com')
        """
        if '@' in email:
            return email.split('@')[1].lower()
        return ''
    
    def _is_company_domain(self, email: str) -> bool:
        """
        Check if email belongs to company domain.
        
        Args:
            email: Email address
            
        Returns:
            True if email domain matches company domain
        """
        domain = self._extract_domain(email)
        return domain == settings.COMPANY_DOMAIN.lower()
    
    def _get_recruiter_admin(self, email: str) -> Optional[RecruiterAdmin]:
        """
        Get recruiter admin by email.
        
        Args:
            email: Email address
            
        Returns:
            RecruiterAdmin object or None
        """
        return self.db.query(RecruiterAdmin).filter(
            RecruiterAdmin.email_id == email.lower()
        ).first()
    
    def _get_candidate_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """
        Get candidate by candidate ID (UUID).
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Candidate object or None
        """
        return self.db.query(Candidate).filter(
            Candidate.candidate_id == candidate_id
        ).first()
    
    def _get_candidate_by_email(self, email: str) -> Optional[Candidate]:
        """
        Get candidate by email.
        
        Args:
            email: Email address
            
        Returns:
            Candidate object or None
        """
        return self.db.query(Candidate).filter(
            Candidate.email_id == email.lower()
        ).first()
    
    def _get_user_type_from_role_id(self, role_id: int) -> UserType:
        """
        Map role_id to UserType enum.
        
        Args:
            role_id: Role ID from database
                - 0 = Candidate
                - 1 = Recruiter
                - 2 = Admin
        
        Returns:
            UserType enum value
        """
        if role_id == 0:
            return UserType.CANDIDATE
        elif role_id == 1:
            return UserType.RECRUITER
        elif role_id == 2:
            return UserType.ADMIN
        else:
            # Default to candidate for unknown role_id
            return UserType.CANDIDATE
    
    def authenticate_admin_recruiter(self, token: str) -> AuthResponse:
        """
        Authenticate admin/recruiter user.
        
        Flow:
        1. Verify Google token
        2. Check if domain is company domain
        3. Check if user exists in RECRUITER_ADMIN table
        
        Args:
            token: Google OAuth ID token
            
        Returns:
            AuthResponse with user type and status
        """
        # Verify Google token
        user_info = self.google_oauth.verify_google_token(token)
        if not user_info:
            return AuthResponse(
                success=False,
                message="Invalid Google token"
            )
        
        email = user_info.get('email', '').lower()
        
        # Check if domain matches company domain
        if not self._is_company_domain(email):
            return AuthResponse(
                success=False,
                message="Email domain does not match company domain"
            )
        
        # Check if user exists in RECRUITER_ADMIN table
        recruiter = self._get_recruiter_admin(email)
        if not recruiter:
            # Domain matches but not in recruiter table - treat as candidate
            return self._handle_candidate_authentication(email, user_info.get('name'))
        
        # Determine user_type based on role_id
        user_type = self._get_user_type_from_role_id(recruiter.role_id)
        
        # User is admin/recruiter
        return AuthResponse(
            success=True,
            message="Authentication successful",
            user_type=user_type,
            email=email,
            name=user_info.get('name'),
            status=None,
            candidate_id=None
        )
    
    def authenticate_candidate(self, token: str, candidate_id: str) -> AuthResponse:
        """
        Authenticate candidate user.
        
        Flow:
        1. Verify Google token
        2. Check if candidate_id exists in CANDIDATE table
        3. Check if email matches
        4. Return status for frontend to handle routing
        
        Args:
            token: Google OAuth ID token
            candidate_id: Candidate UUID
            
        Returns:
            AuthResponse with status and candidate_id
        """
        # Verify Google token
        user_info = self.google_oauth.verify_google_token(token)
        if not user_info:
            return AuthResponse(
                success=False,
                message="Invalid Google token"
            )
        
        email = user_info.get('email', '').lower()
        
        # Check if candidate exists
        candidate = self._get_candidate_by_id(candidate_id)
        if not candidate:
            return AuthResponse(
                success=False,
                message="Candidate not found"
            )
        
        # Check if email matches
        if candidate.email_id.lower() != email:
            return AuthResponse(
                success=False,
                message="Email does not match candidate record"
            )
        
        # Determine user_type based on role_id (should be 0 for candidates)
        user_type = self._get_user_type_from_role_id(candidate.role_id)
        
        # Verify candidate has correct role_id
        if candidate.role_id != 0:
            return AuthResponse(
                success=False,
                message=f"Invalid role_id for candidate: {candidate.role_id}. Expected 0."
            )
        
        # Handle status-based routing
        status = candidate.status.lower()
        
        # Auto-assign system design question if status is 'scheduled' and question not assigned
        if status == 'scheduled':
            try:
                from services.question_assignment_service import QuestionAssignmentService
                assignment_service = QuestionAssignmentService(self.db)
                
                # Check if question already assigned
                if not assignment_service.get_assigned_question(candidate_id):
                    # Auto-assign question based on job role
                    assignment_result = assignment_service.assign_question_to_candidate(candidate_id)
                    if assignment_result.get("success"):
                        logger.info(f"Auto-assigned system design question to candidate {candidate_id}: {assignment_result.get('question_uuid')}")
                    else:
                        logger.warning(f"Failed to auto-assign question to candidate {candidate_id}: {assignment_result.get('message')}")
            except Exception as e:
                # Don't fail authentication if assignment fails
                logger.error(f"Error auto-assigning question to candidate {candidate_id}: {str(e)}")
        
        # Check for 'in progress' status - multiple login error
        if status == 'in progress':
            return AuthResponse(
                success=False,
                message="Multiple login detected. Test is already in progress.",
                status=CandidateStatus.IN_PROGRESS
            )
        
        # Map status to enum
        status_enum = None
        if status == 'shortlisted':
            status_enum = CandidateStatus.SHORTLISTED
        elif status == 'rejected':
            status_enum = CandidateStatus.REJECTED
        elif status == 'scheduled':
            status_enum = CandidateStatus.SCHEDULED
        elif status == 'in progress':
            status_enum = CandidateStatus.IN_PROGRESS
        elif status == 'completed':
            status_enum = CandidateStatus.COMPLETED
        elif status == 'selected':
            status_enum = CandidateStatus.SELECTED
        elif status == 'not selected':
            status_enum = CandidateStatus.NOT_SELECTED
        else:
            return AuthResponse(
                success=False,
                message=f"Invalid candidate status: {status}"
            )
        
        return AuthResponse(
            success=True,
            message="Authentication successful",
            user_type=user_type,
            email=email,
            name=user_info.get('name'),
            status=status_enum,
            candidate_id=candidate_id
        )
    
    def _handle_candidate_authentication(self, email: str, name: Optional[str] = None) -> AuthResponse:
        """
        Handle candidate authentication for users with company domain but not in recruiter table.
        
        Args:
            email: Email address
            name: User name (optional)
            
        Returns:
            AuthResponse with status and candidate_id
        """
        # Check if candidate exists by email
        candidate = self._get_candidate_by_email(email)
        if not candidate:
            # User not found anywhere - access denied
            return AuthResponse(
                success=False,
                message="Access denied. User not found in database."
            )
        
        # Determine user_type based on role_id (should be 0 for candidates)
        user_type = self._get_user_type_from_role_id(candidate.role_id)
        
        # Verify candidate has correct role_id
        if candidate.role_id != 0:
            return AuthResponse(
                success=False,
                message=f"Invalid role_id for candidate: {candidate.role_id}. Expected 0."
            )
        
        # Handle status-based routing
        status = candidate.status.lower()
        
        # Check for 'in progress' status - multiple login error
        if status == 'in progress':
            return AuthResponse(
                success=False,
                message="Multiple login detected. Test is already in progress.",
                status=CandidateStatus.IN_PROGRESS
            )
        
        # Map status to enum
        status_enum = None
        if status == 'shortlisted':
            status_enum = CandidateStatus.SHORTLISTED
        elif status == 'rejected':
            status_enum = CandidateStatus.REJECTED
        elif status == 'scheduled':
            status_enum = CandidateStatus.SCHEDULED
        elif status == 'in progress':
            status_enum = CandidateStatus.IN_PROGRESS
        elif status == 'completed':
            status_enum = CandidateStatus.COMPLETED
        elif status == 'selected':
            status_enum = CandidateStatus.SELECTED
        elif status == 'not selected':
            status_enum = CandidateStatus.NOT_SELECTED
        else:
            return AuthResponse(
                success=False,
                message=f"Invalid candidate status: {status}"
            )
        
        return AuthResponse(
            success=True,
            message="Authentication successful",
            user_type=user_type,
            email=email,
            name=name,
            status=status_enum,
            candidate_id=candidate.candidate_id
        )
    
    def authenticate_user(self, token: str, candidate_id: Optional[str] = None) -> AuthResponse:
        """
        Main authentication method that routes based on user type.
        
        Args:
            token: Google OAuth ID token
            candidate_id: Optional candidate UUID (for candidate login)
            
        Returns:
            AuthResponse with user type, status, and candidate_id
        """
        logger.info("Starting authenticate_user")
        
        # Verify Google token first
        user_info = self.google_oauth.verify_google_token(token)
        if not user_info:
            logger.warning("Google token verification failed")
            return AuthResponse(
                success=False,
                message="Invalid Google token"
            )
        
        email = user_info.get('email', '').lower()
        logger.info(f"Token verified, user email: {email}")
        
        # If candidate_id is provided, authenticate as candidate
        if candidate_id:
            return self.authenticate_candidate(token, candidate_id)
        
        # Check if domain matches company domain
        logger.info(f"Checking domain for email: {email}")
        
        if self._is_company_domain(email):
            logger.info(f"Email {email} matches company domain")
            # Check if user is in recruiter table
            try:
                recruiter = self._get_recruiter_admin(email)
                logger.info(f"Recruiter query result: {recruiter is not None}")
                if recruiter:
                    logger.info(f"Recruiter object: email_id={recruiter.email_id}, role_id={recruiter.role_id}, name={recruiter.name}")
            except Exception as e:
                logger.error(f"Error querying recruiter: {str(e)}", exc_info=True)
                recruiter = None
            
            if recruiter:
                # Log recruiter details for debugging
                logger.info(f"Recruiter found: email={email}, role_id={recruiter.role_id}, name={recruiter.name}")
                
                # Determine user_type based on role_id (1 = Recruiter, 2 = Admin)
                user_type = self._get_user_type_from_role_id(recruiter.role_id)
                logger.info(f"User type determined: {user_type.value} (from role_id={recruiter.role_id})")
                
                # Admin/Recruiter login
                response = AuthResponse(
                    success=True,
                    message="Authentication successful",
                    user_type=user_type,
                    email=email,
                    name=user_info.get('name'),
                    status=None,
                    candidate_id=None
                )
                logger.info(f"Returning successful auth response: user_type={response.user_type.value if response.user_type else None}")
                return response
            else:
                logger.info(f"Recruiter not found for {email}, treating as candidate")
                # Domain matches but not in recruiter table - treat as candidate
                return self._handle_candidate_authentication(email, user_info.get('name'))
        else:
            logger.info(f"Email {email} does NOT match company domain")
            # Not company domain - check if candidate exists
            candidate = self._get_candidate_by_email(email)
            if candidate:
                # Determine user_type based on role_id (should be 0 for candidates)
                user_type = self._get_user_type_from_role_id(candidate.role_id)
                
                # Verify candidate has correct role_id
                if candidate.role_id != 0:
                    return AuthResponse(
                        success=False,
                        message=f"Invalid role_id for candidate: {candidate.role_id}. Expected 0."
                    )
                
                # Candidate exists - handle status-based routing
                status = candidate.status.lower()
                
                if status == 'in progress':
                    return AuthResponse(
                        success=False,
                        message="Multiple login detected. Test is already in progress.",
                        status=CandidateStatus.IN_PROGRESS
                    )
                
                # Map status to enum
                status_enum = None
                if status == 'shortlisted':
                    status_enum = CandidateStatus.SHORTLISTED
                elif status == 'rejected':
                    status_enum = CandidateStatus.REJECTED
                elif status == 'scheduled':
                    status_enum = CandidateStatus.SCHEDULED
                elif status == 'in progress':
                    status_enum = CandidateStatus.IN_PROGRESS
                elif status == 'completed':
                    status_enum = CandidateStatus.COMPLETED
                elif status == 'selected':
                    status_enum = CandidateStatus.SELECTED
                elif status == 'not selected':
                    status_enum = CandidateStatus.NOT_SELECTED
                else:
                    return AuthResponse(
                        success=False,
                        message=f"Invalid candidate status: {status}"
                    )
                
                return AuthResponse(
                    success=True,
                    message="Authentication successful",
                    user_type=user_type,
                    email=email,
                    name=user_info.get('name'),
                    status=status_enum,
                    candidate_id=candidate.candidate_id
                )
        
        # User not found anywhere - access denied
        return AuthResponse(
            success=False,
            message="Access denied. User not found in database."
        )
