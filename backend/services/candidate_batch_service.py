"""
Candidate Batch Service
Handles batch addition of candidates from resume files.
"""
import uuid
import logging
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
from presidio_analyzer import AnalyzerEngine

logger = logging.getLogger(__name__)


class CandidateBatchService:
    """Service for batch processing candidate resumes."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.pii_analyzer = AnalyzerEngine()
    
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
            # Detect PII entities
            results = self.pii_analyzer.analyze(text=text, language='en')
            
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
    
    def process_batch_candidates(
        self,
        job_id: str,
        files: List[UploadFile],
        recruiter_email: str
    ) -> Dict[str, Any]:
        """
        Process batch of candidate resumes (up to 10 files).
        
        Flow:
        1. Extract text from PDF/DOCX files
        2. Extract PII details (for candidate fields only)
        3. Scrub PII from resume text
        4. Calculate resume score (using scrubbed resume)
        5. Create candidate records
        6. Assign candidates to job
        
        Args:
            job_id: Job UUID
            files: List of UploadFile objects (PDF/DOCX)
            recruiter_email: Email of recruiter/admin
            
        Returns:
            Dictionary with processing results
        """
        # Validate file count
        if len(files) > 10:
            return {
                "success": False,
                "message": f"Maximum 10 files allowed. Received {len(files)} files.",
                "total_files": len(files),
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
                "total_files": len(files),
                "successful": 0,
                "failed": 0,
                "candidates": [],
                "failed_files": []
            }
        
        successful_candidates = []
        failed_files = []
        
        # Process each file
        for file in files:
            try:
                # Step 1: Extract text from file
                original_text = file_extractor.extract_text(file)
                if not original_text or not original_text.strip():
                    failed_files.append({
                        "filename": file.filename or "unknown",
                        "error": "No text extracted from file. File may be corrupted or empty."
                    })
                    continue
                
                # Step 2: Extract PII details (ONLY for candidate record fields)
                pii_data = self.extract_pii_for_candidate_fields(original_text)
                
                # Validate required fields
                if not pii_data.get("name"):
                    pii_data["name"] = f"Unknown_{uuid.uuid4().hex[:8]}"
                if not pii_data.get("email"):
                    # Generate placeholder email if not found
                    pii_data["email"] = f"candidate_{uuid.uuid4().hex[:8]}@placeholder.com"
                
                # Step 3: Scrub PII from resume text (for processing and storage)
                scrubbed_resume = pii_scrubber.scrub_pii(original_text)
                
                # Validate no PII remains
                if not pii_scrubber.validate_no_pii(scrubbed_resume):
                    logger.warning(f"PII still detected in scrubbed resume for {file.filename}. Re-scrubbing...")
                    scrubbed_resume = pii_scrubber.scrub_pii(scrubbed_resume)
                
                # Step 4: Calculate resume score (using SCRUBBED resume, NO PII)
                resume_score = resume_scorer.calculate_score(
                    scrubbed_resume=scrubbed_resume,  # NO PII
                    job_description=job.job_description
                )
                
                # Determine initial status based on resume score
                # Threshold: 70 (candidates with score >= 70 are shortlisted)
                initial_status = 'shortlisted' if resume_score >= 70.0 else 'rejected'
                
                # Step 5: Create candidate record
                candidate_id = str(uuid.uuid4())
                
                # Check if email already exists
                existing_candidate = self.db.query(Candidate).filter(
                    Candidate.email_id == pii_data["email"].lower()
                ).first()
                
                if existing_candidate:
                    failed_files.append({
                        "filename": file.filename or "unknown",
                        "error": f"Candidate with email {pii_data['email']} already exists"
                    })
                    continue
                
                new_candidate = Candidate(
                    candidate_id=candidate_id,
                    name=pii_data["name"],  # From PII extraction
                    email_id=pii_data["email"].lower(),  # From PII extraction
                    phone_number=pii_data.get("phone"),  # From PII extraction (optional)
                    location=pii_data.get("location"),  # From PII extraction (optional)
                    resume=scrubbed_resume,  # NO PII, scrubbed version
                    resume_score=resume_score,  # Calculated from scrubbed resume
                    role_id=0,  # Candidate role
                    status=initial_status  # 'shortlisted' or 'rejected' based on score
                )
                
                self.db.add(new_candidate)
                
                # Step 6: Assign candidate to job
                assignment = RecruiterAdminCandidate(
                    recruiter_admin_email=recruiter_email.lower(),
                    candidate_id=candidate_id,
                    job_id=job_id,
                    assigned_at=date.today()
                )
                
                self.db.add(assignment)
                self.db.commit()
                
                successful_candidates.append({
                    "candidate_id": candidate_id,
                    "name": pii_data["name"],
                    "email_id": pii_data["email"],
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
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                failed_files.append({
                    "filename": file.filename or "unknown",
                    "error": f"Processing error: {str(e)}"
                })
                continue
        
        # Build response
        total_files = len(files)
        successful_count = len(successful_candidates)
        failed_count = len(failed_files)
        
        message = f"Processed {total_files} file(s). {successful_count} successful, {failed_count} failed."
        
        return {
            "success": failed_count == 0,
            "message": message,
            "total_files": total_files,
            "successful": successful_count,
            "failed": failed_count,
            "candidates": successful_candidates,
            "failed_files": failed_files
        }

