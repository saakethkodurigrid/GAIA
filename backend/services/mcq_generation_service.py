"""
MCQ Generation Service
Handles MCQ question generation using RAG and LLM
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from utils.mcq.pii_scrubber import pii_scrubber
from utils.mcq.resume_parser import resume_parser
from utils.mcq.dynamic_mapper import get_dynamic_mapper
from utils.mcq.domain_mapper import domain_mapper
from utils.mcq.question_generator import get_question_generator
from services.mcq_rag_service import rag_system
from models.interview_mcq import InterviewMCQ
from schemas.mcq import GenerateMCQRequest, MCQQuestion, MCQGenerationMetadata

logger = logging.getLogger(__name__)


class MCQGenerationService:
    """Service for generating MCQ questions using RAG"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db
        self._rag_initialized = False
    
    def _ensure_rag_initialized(self):
        """Ensure RAG system is initialized"""
        if not self._rag_initialized:
            try:
                logger.info("Initializing RAG system...")
                rag_system.initialize_vector_store(force_recreate=False)
                self._rag_initialized = True
                logger.info("RAG system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG system: {e}")
                # Don't raise error, try to continue - RAG might already be initialized
                self._rag_initialized = True
    
    async def generate_questions(self, request: GenerateMCQRequest) -> Dict[str, Any]:
        """
        Generate MCQ questions based on resume, JD, and grade
        
        Args:
            request: GenerateMCQRequest with resume, job_description, and grade
            
        Returns:
            Dictionary with questions list and metadata
        """
        # Ensure RAG is initialized
        self._ensure_rag_initialized()
        
        try:
            # Step 1: Scrub PII from resume and JD
            logger.info("Scrubbing PII from inputs...")
            scrubbed_resume = pii_scrubber.scrub_pii(request.resume)
            scrubbed_jd = pii_scrubber.scrub_pii(request.job_description)
            
            # Validate no PII remains
            if not pii_scrubber.validate_no_pii(scrubbed_resume):
                logger.warning("PII still detected in resume after scrubbing")
            if not pii_scrubber.validate_no_pii(scrubbed_jd):
                logger.warning("PII still detected in JD after scrubbing")
            
            # Step 2: Parse resume and JD (for skills extraction)
            logger.info("Parsing resume and JD...")
            resume_data = resume_parser.parse_resume(request.resume)
            jd_data = resume_parser.parse_jd(request.job_description)
            
            # Step 3: Determine role (basic extraction for reference)
            role = jd_data.get("role_type", "Unknown")
            
            # Step 4: Use dynamic LLM-based mapping for domain
            logger.info("Using LLM to dynamically map role to domain...")
            dynamic_mapper = get_dynamic_mapper()
            domain = await dynamic_mapper.map_role_to_domain(
                role=role,
                jd_text=scrubbed_jd,
                resume_text=scrubbed_resume
            )
            
            if domain is None:
                logger.warning(f"No domain found for role: {role}. Will generate without RAG examples.")
                domain = "general"
            else:
                logger.info(f"Mapped role '{role}' to domain: {domain}")
            
            # Step 5: Use dynamic LLM-based subtopic identification
            logger.info("Using LLM to identify relevant subtopics...")
            subtopics = await dynamic_mapper.identify_relevant_subtopics(
                domain=domain,
                jd_text=scrubbed_jd,
                resume_text=scrubbed_resume
            )
            
            if not subtopics:
                logger.warning("No subtopics identified, using fallback")
                subtopics = domain_mapper.get_relevant_subtopics(
                    scrubbed_jd,
                    scrubbed_resume,
                    domain
                )
            else:
                logger.info(f"Identified {len(subtopics)} relevant subtopics")
            
            # Step 6: Combine skills (for RAG query construction)
            all_skills = resume_parser.combine_skills(resume_data, jd_data)
            
            # Step 7: Generate questions with full context
            logger.info(f"Generating questions for role: {role}, domain: {domain}, grade: {request.grade}")
            generator = get_question_generator()
            
            questions = await generator.generate_questions(
                scrubbed_resume_text=scrubbed_resume,
                scrubbed_jd_text=scrubbed_jd,
                resume_skills=resume_data.get("technologies", []),
                jd_skills=jd_data.get("technologies", []),
                role=role,
                grade=request.grade,
                domain=domain,
                subtopics=subtopics,
                count=25
            )
            
            if len(questions) < 25:
                logger.warning(f"Only generated {len(questions)} questions, expected 25")
            
            # Step 8: Calculate metadata
            difficulty_dist = {}
            for q in questions:
                diff = q.get("difficulty", "unknown")
                difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
            
            metadata = MCQGenerationMetadata(
                total_questions=len(questions),
                difficulty_distribution=difficulty_dist,
                domain=domain,
                subtopics_covered=subtopics[:10]  # Top 10 subtopics
            )
            
            return {
                "questions": questions,
                "metadata": metadata
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Error generating questions: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate questions: {str(e)}")
    
    def save_generated_questions(
        self,
        candidate_id: str,
        questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save generated questions to InterviewMCQ table
        
        Args:
            candidate_id: UUID of the candidate
            questions: List of generated question dictionaries
            
        Returns:
            Dictionary with success status and count
        """
        try:
            saved_count = 0
            failed_count = 0
            
            for question in questions:
                try:
                    # Generate UUID for the question
                    question_uuid = str(uuid.uuid4())
                    
                    # Get correct option number
                    correct_option = question.get("correct_option", 1)
                    # Ensure correct_option is between 1 and 4
                    if not (1 <= correct_option <= 4):
                        correct_option = 1
                    
                    options = [
                        question.get("option1", ""),
                        question.get("option2", ""),
                        question.get("option3", ""),
                        question.get("option4", "")
                    ]
                    
                    # Prepare tags (only original tags, not options)
                    tags = {
                        "original_tags": question.get("tags", [])
                    }
                    
                    # Create InterviewMCQ record
                    mcq_record = InterviewMCQ(
                        uuid=question_uuid,
                        candidate_id=candidate_id,
                        question=question.get("question", ""),
                        correct_answer=correct_option,  # Store option number (1, 2, 3, or 4)
                        candidate_answer=None,  # Will be filled when candidate answers (will store option number)
                        score=None,  # Will be calculated after submission
                        options=options,  # Save options to dedicated column
                        tags=tags,  # Only original tags
                        difficulty=question.get("difficulty", "medium")
                    )
                    
                    self.db.add(mcq_record)
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to save question: {str(e)}")
                    failed_count += 1
                    continue
            
            # Commit all saved questions
            if saved_count > 0:
                self.db.commit()
            
            return {
                "success": saved_count > 0,
                "saved_count": saved_count,
                "failed_count": failed_count,
                "message": f"Saved {saved_count} questions, {failed_count} failed"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving questions: {e}", exc_info=True)
            raise RuntimeError(f"Failed to save questions: {str(e)}")
    
    def initialize_rag(self, force_recreate: bool = False) -> Dict[str, Any]:
        """
        Initialize or reinitialize RAG system
        
        Args:
            force_recreate: If True, recreate the vector store
            
        Returns:
            Dictionary with status and message
        """
        try:
            logger.info("Initializing RAG system...")
            rag_system.initialize_vector_store(force_recreate=force_recreate)
            self._rag_initialized = True
            return {
                "status": "success",
                "message": "RAG system initialized successfully"
            }
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
            raise RuntimeError(f"Failed to initialize RAG: {str(e)}")
