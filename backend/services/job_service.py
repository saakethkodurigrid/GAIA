"""
Job service for managing jobs.
"""
import uuid
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
        
        # Create new job
        try:
            new_job = Job(
                job_id=job_id,
                job_role=request.job_role,
                job_description=request.job_description,
                recruiter_email_id=recruiter_email.lower()
            )
            
            self.db.add(new_job)
            self.db.commit()
            self.db.refresh(new_job)
            
            return AddJobResponse(
                success=True,
                message="Job added successfully",
                data=JobResponse(
                    job_id=new_job.job_id,
                    job_role=new_job.job_role,
                    job_description=new_job.job_description,
                    recruiter_email_id=new_job.recruiter_email_id
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
                    job_id=job.job_id,
                    job_role=job.job_role,
                    job_description=job.job_description,
                    recruiter_email_id=job.recruiter_email_id
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

