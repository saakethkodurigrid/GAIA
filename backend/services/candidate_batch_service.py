"""
Candidate Batch Service
Handles batch addition of candidates from resume files.
"""
import uuid
import logging
import asyncio
import threading
from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile
from models.candidate import Candidate
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.job import Job
from utils.resume.file_extractor import file_extractor
from utils.resume.resume_scorer import resume_scorer
from utils.mcq.pii_scrubber import pii_scrubber
from services.email_service import email_service
from services.candidate_service import CandidateService
from core.config import settings

logger = logging.getLogger(__name__)


class CandidateBatchService:
    """Service for batch processing candidate resumes."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def extract_pii_for_candidate_fields(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract PII details for candidate record fields only.
        These are NOT used in resume scoring or stored in resume text.
        
        Args:
            text: Original resume text
            
        Returns:
            Dictionary with name, email, phone, location
        """
        pii_data = {
            "name": None,
            "email": None,
            "phone": None,
            "location": None
        }
        
        try:
            # Detect PII entities - use global pii_scrubber analyzer to avoid duplicate initialization
            results = pii_scrubber.analyzer.analyze(text=text, language='en')
            
            # Extract first occurrence of each PII type
            for result in results:
                entity_type = result.entity_type
                start = result.start
                end = result.end
                value = text[start:end]
                
                if entity_type == 'PERSON' and not pii_data["name"]:
                    pii_data["name"] = value.strip()
                elif entity_type == 'EMAIL_ADDRESS' and not pii_data["email"]:
                    pii_data["email"] = value.strip()
                elif entity_type == 'PHONE_NUMBER' and not pii_data["phone"]:
                    pii_data["phone"] = value.strip()
                elif entity_type == 'LOCATION' and not pii_data["location"]:
                    pii_data["location"] = value.strip()
            
            # If name not found, try to extract from first line
            if not pii_data["name"]:
                first_line = text.split('\n')[0].strip()
                if first_line and len(first_line) < 100:  # Reasonable name length
                    pii_data["name"] = first_line
            
            # If email not found, try regex
            if not pii_data["email"]:
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                matches = re.findall(email_pattern, text)
                if matches:
                    pii_data["email"] = matches[0]
            
        except Exception as e:
            logger.warning(f"Error extracting PII: {str(e)}")
        
        return pii_data
    
    async def process_single_candidate(
        self,
        job_id: str,
        candidate_data: Dict[str, Any],
        recruiter_email: str
    ) -> Dict[str, Any]:
        """
        Process a single candidate and return result immediately.
        
        Used for streaming responses where we need to return results one at a time.
        
        Args:
            job_id: Job UUID
            candidate_data: Dict with keys: name, email, file (UploadFile)
            recruiter_email: Email of recruiter/admin
            
        Returns:
            Dictionary with either:
            - success: True, candidate: {...} (on success)
            - success: False, failed_file: {...} (on failure)
        """
        name = candidate_data["name"]
        email = candidate_data["email"]
        file = candidate_data["file"]
        
        try:
            # Step 1: Extract text from file
            original_text = file_extractor.extract_text(file)
            if not original_text or not original_text.strip():
                return {
                    "success": False,
                    "failed_file": {
                        "filename": file.filename or "unknown",
                        "error": "No text extracted from file. File may be corrupted or empty."
                    }
                }
            
            # Step 2: Scrub PII from resume text
            scrubbed_resume = pii_scrubber.scrub_pii(original_text)
            
            # Validate no PII remains
            if not pii_scrubber.validate_no_pii(scrubbed_resume):
                logger.warning(f"PII still detected in scrubbed resume for {file.filename}. Re-scrubbing...")
                scrubbed_resume = pii_scrubber.scrub_pii(scrubbed_resume)
            
            # Get job details
            job = self.db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                return {
                    "success": False,
                    "failed_file": {
                        "filename": file.filename or "unknown",
                        "error": f"Job with ID {job_id} not found"
                    }
                }
            
            # Step 3: Calculate resume score
            resume_score = await resume_scorer.calculate_score(
                scrubbed_resume=scrubbed_resume,
                job_description=job.job_description,
                grade=job.grade,
                role_name=job.job_role
            )
            
            # Determine initial status
            initial_status = 'shortlisted' if resume_score >= settings.RESUME_SCORE_THRESHOLD else 'rejected'
            
            # Step 4: Create candidate record
            candidate_id = str(uuid.uuid4())
            candidate_service = CandidateService(self.db)
            candidate_reference_number = candidate_service._generate_candidate_reference_number(candidate_id)
            
            # Check for existing assignment
            existing_assignment = self.db.query(RecruiterAdminCandidate).join(
                Candidate,
                RecruiterAdminCandidate.candidate_id == Candidate.candidate_id
            ).filter(
                Candidate.email_id == email.lower(),
                RecruiterAdminCandidate.job_id == job_id
            ).first()
            
            if existing_assignment:
                return {
                    "success": False,
                    "failed_file": {
                        "filename": file.filename or "unknown",
                        "error": f"Candidate with email {email} is already assigned to this job"
                    }
                }
            
            new_candidate = Candidate(
                candidate_id=candidate_id,
                candidate_reference_number=candidate_reference_number,
                name=name,
                email_id=email.lower(),
                phone_number=None,
                location=None,
                resume=scrubbed_resume,
                resume_score=resume_score,
                role_id=0,
                status=initial_status
            )
            
            self.db.add(new_candidate)
            
            # Step 5: Assign candidate to job
            assignment = RecruiterAdminCandidate(
                recruiter_admin_email=recruiter_email.lower(),
                candidate_id=candidate_id,
                job_id=job_id,
                assigned_at=date.today()
            )
            
            self.db.add(assignment)
            self.db.commit()
            
            # Step 6: Send email if shortlisted (async, non-blocking)
            if initial_status == 'shortlisted' and resume_score >= settings.RESUME_SCORE_THRESHOLD:
                try:
                    job_role = job.job_role if job else "Technical Interview"
                    
                    def send_email_async():
                        try:
                            asyncio.run(
                                email_service.send_scheduling_invitation_email(
                                    candidate_email=email.lower(),
                                    candidate_name=name,
                                    candidate_id=candidate_id,
                                    job_role=job_role,
                                    resume_score=resume_score
                                )
                            )
                        except Exception as e:
                            logger.error(f"Error in background email thread: {str(e)}")
                    
                    email_thread = threading.Thread(target=send_email_async, daemon=True)
                    email_thread.start()
                    logger.info(f"Scheduling invitation email queued for candidate {candidate_id}")
                except Exception as e:
                    logger.error(f"Failed to queue scheduling invitation email to {email}: {str(e)}")
            
            return {
                "success": True,
                "candidate": {
                    "candidate_id": candidate_reference_number,  # Return reference number for consistency
                    "name": name,
                    "email_id": email,
                    "status": initial_status,
                    "resume_score": round(resume_score, 2),
                    "processing_status": "success",
                    "errors": None
                }
            }
            
        except IntegrityError as e:
            self.db.rollback()
            return {
                "success": False,
                "failed_file": {
                    "filename": file.filename or "unknown",
                    "error": f"Database error: {str(e)}"
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing candidate {name} ({email}): {str(e)}")
            return {
                "success": False,
                "failed_file": {
                    "filename": file.filename or "unknown",
                    "error": f"Processing error: {str(e)}"
                }
            }
    
    async def process_batch_candidates(
        self,
        job_id: str,
        candidate_data_list: List[Dict[str, Any]],
        recruiter_email: str
    ) -> Dict[str, Any]:
        """
        Process batch of candidates (up to 10) with provided name, email, and resume files.
        
        Flow:
        1. Extract text from PDF/DOCX resume files
        2. Use provided name and email (no PII extraction needed)
        3. Scrub PII from resume text (for storage and scoring)
        4. Calculate resume score (using scrubbed resume)
        5. Create candidate records with provided name/email
        6. Assign candidates to job
        
        Args:
            job_id: Job UUID
            candidate_data_list: List of dicts with keys: name, email, file (UploadFile)
            recruiter_email: Email of recruiter/admin
            
        Returns:
            Dictionary with processing results
        """
        # Validate candidate count
        if len(candidate_data_list) > 10:
            return {
                "success": False,
                "message": f"Maximum 10 candidates allowed. Received {len(candidate_data_list)} candidates.",
                "total_files": len(candidate_data_list),
                "successful": 0,
                "failed": 0,
                "candidates": [],
                "failed_files": []
            }
        
        # Verify job exists
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return {
                "success": False,
                "message": f"Job with ID {job_id} not found",
                "total_files": len(candidate_data_list),
                "successful": 0,
                "failed": 0,
                "candidates": [],
                "failed_files": []
            }
        
        successful_candidates = []
        failed_files = []
        
        # Process each candidate
        for candidate_data in candidate_data_list:
            name = candidate_data["name"]
            email = candidate_data["email"]
            file = candidate_data["file"]
            
            try:
                # Step 1: Extract text from file
                original_text = file_extractor.extract_text(file)
                if not original_text or not original_text.strip():
                    failed_files.append({
                        "filename": file.filename or "unknown",
                        "error": "No text extracted from file. File may be corrupted or empty."
                    })
                    continue
                
                # Step 2: Scrub PII from resume text (for processing and storage)
                scrubbed_resume = pii_scrubber.scrub_pii(original_text)
                
                # Validate no PII remains
                if not pii_scrubber.validate_no_pii(scrubbed_resume):
                    logger.warning(f"PII still detected in scrubbed resume for {file.filename}. Re-scrubbing...")
                    scrubbed_resume = pii_scrubber.scrub_pii(scrubbed_resume)
                
                # Step 3: Calculate resume score (using SCRUBBED resume, NO PII)
                resume_score = await resume_scorer.calculate_score(
                    scrubbed_resume=scrubbed_resume,  # NO PII
                    job_description=job.job_description,
                    grade=job.grade,  # Pass the grade from job for role-specific evaluation
                    role_name=job.job_role  # Pass the role name for role-specific experience evaluation
                )
                
                # Determine initial status based on resume score
                # Uses RESUME_SCORE_THRESHOLD from config (candidates with score >= threshold are shortlisted)
                initial_status = 'shortlisted' if resume_score >= settings.RESUME_SCORE_THRESHOLD else 'rejected'
                
                # Step 4: Create candidate record
                candidate_id = str(uuid.uuid4())
                
                # Generate candidate reference number
                candidate_service = CandidateService(self.db)
                candidate_reference_number = candidate_service._generate_candidate_reference_number(candidate_id)
                
                # Check if candidate with this email is already assigned to THIS SPECIFIC JOB
                # This allows same email in different jobs (with different UUIDs) but prevents duplicates within same job
                existing_assignment = self.db.query(RecruiterAdminCandidate).join(
                    Candidate,
                    RecruiterAdminCandidate.candidate_id == Candidate.candidate_id
                ).filter(
                    Candidate.email_id == email.lower(),
                    RecruiterAdminCandidate.job_id == job_id
                ).first()
                
                if existing_assignment:
                    failed_files.append({
                        "filename": file.filename or "unknown",
                        "error": f"Candidate with email {email} is already assigned to this job"
                    })
                    continue
                
                new_candidate = Candidate(
                    candidate_id=candidate_id,
                    candidate_reference_number=candidate_reference_number,  # Generated reference number
                    name=name,  # From provided data
                    email_id=email.lower(),  # From provided data
                    phone_number=None,  # Not provided, can be updated later
                    location=None,  # Not provided, can be updated later
                    resume=scrubbed_resume,  # NO PII, scrubbed version
                    resume_score=resume_score,  # Calculated from scrubbed resume
                    role_id=0,  # Candidate role
                    status=initial_status  # 'shortlisted' or 'rejected' based on score
                )
                
                self.db.add(new_candidate)
                
                # Step 5: Assign candidate to job
                assignment = RecruiterAdminCandidate(
                    recruiter_admin_email=recruiter_email.lower(),
                    candidate_id=candidate_id,
                    job_id=job_id,
                    assigned_at=date.today()
                )
                
                self.db.add(assignment)
                self.db.commit()
                
                # Step 6: Send scheduling invitation email AUTOMATICALLY if candidate is shortlisted
                if initial_status == 'shortlisted' and resume_score >= settings.RESUME_SCORE_THRESHOLD:
                    try:
                        # Get job role for email
                        job = self.db.query(Job).filter(Job.job_id == job_id).first()
                        job_role = job.job_role if job else "Technical Interview"
                        
                        # Send scheduling invitation email (async, non-blocking)
                        # Use threading to run async function in background
                        import threading
                        
                        def send_email_async():
                            """Helper function to run async email sending in background thread."""
                            try:
                                asyncio.run(
                                    email_service.send_scheduling_invitation_email(
                                        candidate_email=email.lower(),
                                        candidate_name=name,
                                        candidate_id=candidate_id,
                                        job_role=job_role,
                                        resume_score=resume_score
                                    )
                                )
                            except Exception as e:
                                logger.error(f"Error in background email thread: {str(e)}")
                        
                        # Start email sending in background thread
                        email_thread = threading.Thread(target=send_email_async, daemon=True)
                        email_thread.start()
                        
                        logger.info(f"Scheduling invitation email queued for candidate {candidate_id}")
                    except Exception as e:
                        # Don't fail candidate creation if email fails
                        logger.error(f"Failed to queue scheduling invitation email to {email}: {str(e)}")
                
                successful_candidates.append({
                    "candidate_id": candidate_id,
                    "name": name,
                    "email_id": email,
                    "status": initial_status,  # 'shortlisted' or 'rejected'
                    "resume_score": round(resume_score, 2),
                    "processing_status": "success",
                    "errors": None
                })
                
            except IntegrityError as e:
                self.db.rollback()
                failed_files.append({
                    "filename": file.filename or "unknown",
                    "error": f"Database error: {str(e)}"
                })
                continue
            except Exception as e:
                self.db.rollback()
                logger.error(f"Error processing candidate {name} ({email}): {str(e)}")
                failed_files.append({
                    "filename": file.filename or "unknown",
                    "error": f"Processing error: {str(e)}"
                })
                continue
        
        # Build response
        total_files = len(candidate_data_list)
        successful_count = len(successful_candidates)
        failed_count = len(failed_files)
        
        message = f"Processed {total_files} candidate(s). {successful_count} successful, {failed_count} failed."
        
        return {
            "success": failed_count == 0,
            "message": message,
            "total_files": total_files,
            "successful": successful_count,
            "failed": failed_count,
            "candidates": successful_candidates,
            "failed_files": failed_files
        }

