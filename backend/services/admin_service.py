"""
Admin service for managing recruiters and admins.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.recruiter_admin import RecruiterAdmin
from models.role import Role
from schemas.admin import AddRecruiterAdminRequest, AddRecruiterAdminResponse, RecruiterAdminResponse


class AdminService:
    """Admin service class for managing recruiters and admins."""
    
    def __init__(self, db: Session):
        """Initialize admin service with database session."""
        self.db = db
    
    def add_recruiter_admin(self, request: AddRecruiterAdminRequest) -> AddRecruiterAdminResponse:
        """
        Add a new recruiter or admin to the database.
        
        Args:
            request: AddRecruiterAdminRequest with recruiter/admin details
            
        Returns:
            AddRecruiterAdminResponse with success status and data
            
        Raises:
            ValueError: If role_id is invalid or email already exists
        """
        # Validate role_id
        if request.role_id not in [1, 2]:
            return AddRecruiterAdminResponse(
                success=False,
                message=f"Invalid role_id: {request.role_id}. Must be 1 (Recruiter) or 2 (Admin)"
            )
        
        # Check if role exists in ROLE_TABLE
        role = self.db.query(Role).filter(Role.role_id == request.role_id).first()
        if not role:
            return AddRecruiterAdminResponse(
                success=False,
                message=f"Role with role_id {request.role_id} does not exist in ROLE_TABLE"
            )
        
        # Check if email already exists
        existing_recruiter = self.db.query(RecruiterAdmin).filter(
            RecruiterAdmin.email_id == request.email_id.lower()
        ).first()
        
        if existing_recruiter:
            return AddRecruiterAdminResponse(
                success=False,
                message=f"Email {request.email_id} is already registered in the system"
            )
        
        # Create new recruiter/admin
        try:
            new_recruiter = RecruiterAdmin(
                email_id=request.email_id.lower(),
                name=request.name,
                role_id=request.role_id,
                phone_number=request.phone_number,
                location=request.location
            )
            
            self.db.add(new_recruiter)
            self.db.commit()
            self.db.refresh(new_recruiter)
            
            # Get role name for response
            role_name = role.role
            
            return AddRecruiterAdminResponse(
                success=True,
                message=f"{role_name} added successfully",
                data=RecruiterAdminResponse(
                    email_id=new_recruiter.email_id,
                    name=new_recruiter.name,
                    role_id=new_recruiter.role_id,
                    phone_number=new_recruiter.phone_number,
                    location=new_recruiter.location,
                    role_name=role_name
                )
            )
            
        except IntegrityError as e:
            self.db.rollback()
            role_type = "admin" if request.role_id == 2 else "recruiter"
            return AddRecruiterAdminResponse(
                success=False,
                message=f"Failed to add {role_type}. Database constraint violation. Please check if the email already exists."
            )
        except Exception as e:
            self.db.rollback()
            role_type = "admin" if request.role_id == 2 else "recruiter"
            return AddRecruiterAdminResponse(
                success=False,
                message=f"Failed to add {role_type}. An unexpected error occurred: {str(e)}"
            )

