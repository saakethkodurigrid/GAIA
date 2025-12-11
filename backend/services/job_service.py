"""
Job service for managing jobs.
"""
import uuid
import zlib
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.job import Job
from models.recruiter_admin import RecruiterAdmin
from schemas.admin import AddJobRequest, AddJobResponse, JobResponse, ListJobsResponse


class JobService:
    """Job service class for managing jobs."""
    
    def __init__(self, db: Session):
        """Initialize job service with database session."""
        self.db = db
    
    def _generate_job_reference_number(self, uuid_str: str) -> str:
        """
        Generate a unique 6-digit job reference number from UUID.
        Format: JD-XXXXXX (e.g., JD-783901)
        
        Args:
            uuid_str: UUID string to generate reference number from
            
        Returns:
            Formatted job reference number string
        """
        # Use CRC32 hash of UUID to get a number
        hash_value = zlib.crc32(uuid_str.encode())
        # Get 6-digit number (000000-999999)
        display_id = abs(hash_value) % 1000000
        
        # Format as "JD-783901"
        formatted_id = f"JD-{display_id:06d}"
        
        # Check for collision
        existing = self.db.query(Job).filter(Job.job_reference_number == formatted_id).first()
        
        if existing:
            # Collision handling: try with a counter until unique
            counter = 1
            while existing:
                new_hash = zlib.crc32((uuid_str + str(counter)).encode())
                display_id = abs(new_hash) % 1000000
                formatted_id = f"JD-{display_id:06d}"
                existing = self.db.query(Job).filter(Job.job_reference_number == formatted_id).first()
                counter += 1
                
                # Safety check to prevent infinite loop (should never happen in practice)
                if counter > 1000:
                    raise Exception("Unable to generate unique job reference number after 1000 attempts")
        
        return formatted_id
    
    def get_job_by_reference_number(self, job_reference_number: str) -> Job:
        """
        Get job by job_reference_number (e.g., "JD-783901").
        Always fetches from database - no conversion/derivation logic.
        Works even if job_reference_number is manually updated in database.
        
        Args:
            job_reference_number: Job reference number to look up
            
        Returns:
            Job object if found
            
        Raises:
            ValueError: If job with reference number not found
        """
        job = self.db.query(Job).filter(Job.job_reference_number == job_reference_number).first()
        if not job:
            raise ValueError(f"Job with reference number {job_reference_number} not found")
        return job
    
    def get_job_uuid_from_reference_number(self, job_reference_number: str) -> str:
        """
        Get UUID from job_reference_number (legacy method for backward compatibility).
        Uses get_job_by_reference_number internally.
        
        Args:
            job_reference_number: Job reference number to look up
            
        Returns:
            UUID string if found
            
        Raises:
            ValueError: If job with reference number not found
        """
        job = self.get_job_by_reference_number(job_reference_number)
        return job.job_id
    
    def add_job(self, request: AddJobRequest, recruiter_email: str) -> AddJobResponse:
        """
        Add a new job to the database.
        
        Args:
            request: AddJobRequest with job details
            recruiter_email: Email of the recruiter/admin creating the job
            
        Returns:
            AddJobResponse with success status and job data
        """
        # Verify recruiter exists
        recruiter = self.db.query(RecruiterAdmin).filter(
            RecruiterAdmin.email_id == recruiter_email.lower()
        ).first()
        
        if not recruiter:
            return AddJobResponse(
                success=False,
                message="Recruiter/admin not found. Cannot create job."
            )
        
        # Generate UUID for job_id
        job_id = str(uuid.uuid4())
        
        # Generate job reference number from UUID
        job_reference_number = self._generate_job_reference_number(job_id)
        
        # Create new job
        try:
            new_job = Job(
                job_id=job_id,
                job_reference_number=job_reference_number,
                job_role=request.job_role,
                job_description=request.job_description,
                recruiter_email_id=recruiter_email.lower(),
                grade=request.grade
            )
            
            self.db.add(new_job)
            self.db.commit()
            self.db.refresh(new_job)
            
            return AddJobResponse(
                success=True,
                message="Job added successfully",
                data=JobResponse(
                    job_id=new_job.job_reference_number or new_job.job_id,  # Return reference number, fallback to UUID if None
                    job_role=new_job.job_role,
                    job_description=new_job.job_description,
                    recruiter_email_id=new_job.recruiter_email_id,
                    recruiter_name=recruiter.name,  # Include recruiter name from fetched recruiter
                    grade=new_job.grade
                )
            )
            
        except IntegrityError as e:
            self.db.rollback()
            return AddJobResponse(
                success=False,
                message="Failed to add job. Database constraint violation. Please check if the recruiter email is valid."
            )
        except Exception as e:
            self.db.rollback()
            return AddJobResponse(
                success=False,
                message=f"Failed to add job. An unexpected error occurred: {str(e)}"
            )
    
    def list_jobs(self, user_email: str, user_role_id: int) -> ListJobsResponse:
        """
        List jobs based on user role.
        
        - Recruiters (role_id = 1): Only see jobs they created
        - Admins (role_id = 2): See all jobs created by everyone
        
        Args:
            user_email: Email of the current user
            user_role_id: Role ID of the current user (1 = Recruiter, 2 = Admin)
            
        Returns:
            ListJobsResponse with list of jobs
        """
        try:
            # If user is recruiter, filter by their email
            if user_role_id == 1:
                jobs = self.db.query(Job).filter(
                    Job.recruiter_email_id == user_email.lower()
                ).all()
            # If user is admin, get all jobs
            elif user_role_id == 2:
                jobs = self.db.query(Job).all()
            else:
                return ListJobsResponse(
                    success=False,
                    message="Invalid user role. Only recruiters and admins can list jobs.",
                    count=0,
                    jobs=[]
                )
            
            # Convert jobs to response format
            job_list = [
                JobResponse(
                    job_id=job.job_reference_number or job.job_id,  # Return reference number, fallback to UUID if None
                    job_role=job.job_role,
                    job_description=job.job_description,
                    recruiter_email_id=job.recruiter_email_id,
                    recruiter_name=job.recruiter.name if job.recruiter else "Unknown",
                    grade=job.grade
                )
                for job in jobs
            ]
            
            return ListJobsResponse(
                success=True,
                message=f"Successfully retrieved {len(job_list)} job(s)",
                count=len(job_list),
                jobs=job_list
            )
            
        except Exception as e:
            return ListJobsResponse(
                success=False,
                message=f"Failed to retrieve jobs. An unexpected error occurred: {str(e)}",
                count=0,
                jobs=[]
            )

