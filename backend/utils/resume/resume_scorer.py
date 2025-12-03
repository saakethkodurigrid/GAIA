"""
Resume Scorer
Calculates resume score based on match with job description using LLM.
Uses scrubbed resume (no PII) for scoring.
"""
from typing import Dict, Optional
import json
import logging
import re
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage
from core.config import settings
from utils.mcq.resume_parser import resume_parser

logger = logging.getLogger(__name__)


class ResumeScorer:
    """Calculates resume scores based on JD match using LLM."""
    
    def __init__(self):
        """Initialize resume scorer with LLM provider."""
        # Use configured provider with its default model from settings
        # This ensures consistency with the rest of the application
        try:
            self.llm = LLMProviderFactory.create_provider()
            self.model = self.llm.model  # Store the actual model being used
            logger.info(f"Resume scorer initialized with provider: {settings.LLM_PROVIDER}, model: {self.model}")
        except ValueError as e:
            logger.warning(f"{str(e)}. Resume scoring will use fallback method.")
            self.llm = None
            self.model = None
    
    async def calculate_score(self, scrubbed_resume: str, job_description: str) -> float:
        """
        Calculate resume score (0-100) based on match with job description using LLM.
        
        Uses scrubbed resume (no PII) for all calculations.
        
        Args:
            scrubbed_resume: Resume text with PII removed
            job_description: Job description text
            
        Returns:
            Score from 0-100
        """
        if not scrubbed_resume or not job_description:
            return 0.0
        
        # Try LLM-based scoring first
        if self.llm:
            try:
                llm_score = await self._calculate_with_llm(scrubbed_resume, job_description)
                if llm_score is not None:
                    # Ensure score is between 0-100
                    return max(0.0, min(100.0, llm_score))
            except Exception as e:
                logger.warning(f"LLM scoring failed: {str(e)}. Falling back to rule-based method.")
        
        # Fallback to rule-based method
        return self._calculate_with_rules(scrubbed_resume, job_description)
    
    async def _calculate_with_llm(
        self, 
        scrubbed_resume: str, 
        job_description: str
    ) -> Optional[float]:
        """
        Calculate single combined score using LLM.
        
        Args:
            scrubbed_resume: Resume text (scrubbed, no PII)
            job_description: Job description text
            
        Returns:
            Single combined score (0-100) or None if LLM call fails
        """
        # Extract years from resume and JD for context
        resume_years = self._extract_years_from_text(scrubbed_resume)
        jd_years_required = self._extract_years_from_jd(job_description)
        
        prompt = f"""You are an expert recruiter evaluating a candidate's resume against a job description.

Evaluate the candidate's overall fit and provide a SINGLE combined score (0-100) that considers ALL factors:

**Factors to Consider:**

1. **Skill Match**: How well do the candidate's technical skills, technologies, and tools match the job requirements?
   - Required skills, preferred skills, technology stack, frameworks, tools, programming languages
   - Consider both explicit matches and related/equivalent technologies
   - Weight required skills more heavily than nice-to-have skills

2. **Experience Match**: How well does the candidate's experience match the job requirements?
   - **CRITICAL**: Extract the exact years of experience requirement from the JD (e.g., "3+ years", "5-7 years", "minimum 2 years", "at least 4 years")
   - **CRITICAL**: Extract the candidate's years of experience from the resume
   - Compare the candidate's years with the JD requirement:
     * If candidate meets or exceeds requirement: Strong positive impact
     * If candidate is close (within 1-2 years): Moderate positive impact
     * If candidate is below requirement: Negative impact (more negative if significantly below)
   - Also consider: Relevant work experience, project experience, domain expertise, industry experience, quality of experience

3. **Role Relevance**: How relevant is the candidate's background to the specific role?
   - Role type alignment, domain expertise, career progression, responsibilities match, industry fit
   - Consider if candidate's experience aligns with the role's focus area and responsibilities

4. **Other Factors**: Consider any other relevant factors that impact the candidate's fit
   - Education background, certifications, achievements, project complexity, leadership experience, etc.

**Resume (PII removed):**
{scrubbed_resume[:3000]}

**Job Description:**
{job_description[:3000]}

**Extracted Context (for reference):**
- Candidate's years of experience (from resume): {resume_years if resume_years else "Not found"}
- JD years requirement (from job description): {jd_years_required if jd_years_required else "Not specified"}

**Scoring Guidelines:**
- 90-100: Excellent match - candidate strongly meets or exceeds all requirements
- 80-89: Very good match - candidate meets most requirements well
- 70-79: Good match - candidate meets core requirements, some gaps
- 60-69: Moderate match - candidate has some relevant experience but significant gaps
- 50-59: Below average match - candidate has limited relevant experience
- 0-49: Poor match - candidate does not meet most requirements

Provide your evaluation as a JSON object with a single key:
{{
    "score": <number 0-100>
}}

Be precise and objective. Base the score on actual content, not assumptions.
The score should be a single number that holistically represents the candidate's overall fit considering all factors above.
Respond with ONLY the JSON object, no additional text."""

        try:
            messages = [
                LLMMessage(
                    role="system",
                    content="You are a precise recruiter evaluation assistant. Always respond with valid JSON only. Provide a single combined score (0-100) that considers all factors: skills, experience years comparison, role relevance, and other relevant factors."
                ),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=200
            )
            
            content = response.content.strip()
            
            # Extract JSON if wrapped in code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            result = json.loads(content)
            
            # Extract single score
            score = float(result.get("score", 0))
            
            # Ensure score is in valid range
            score = max(0.0, min(100.0, score))
            
            logger.info(f"LLM Combined Score: {score:.1f}")
            
            return score
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}. Content: {content[:200]}")
            return None
        except KeyError as e:
            logger.error(f"Missing 'score' key in LLM response: {e}. Response: {result}")
            return None
        except Exception as e:
            logger.error(f"Error in LLM scoring: {e}")
            return None
    
    def _extract_years_from_text(self, text: str) -> Optional[int]:
        """
        Extract years of experience from resume text.
        
        Args:
            text: Resume text
            
        Returns:
            Years of experience or None if not found
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Patterns to match years of experience
        patterns = [
            r'(\d+)\s*(?:\+)?\s*years?\s+(?:of\s+)?(?:experience|exp)',
            r'(?:experience|exp)[:\s]+(\d+)\s*years?',
            r'(\d+)\s*years?\s+(?:in|of|with)',
            r'(\d+)\+?\s*y\.?o\.?e\.?',  # y.o.e.
            r'(\d+)\+?\s*yrs?\.?\s+(?:exp|experience)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                try:
                    years = int(matches[0])
                    if 0 < years < 50:  # Reasonable range
                        return years
                except (ValueError, IndexError):
                    continue
        
        # Fallback: look for numbers near "year" keywords
        words = text_lower.split()
        for i, word in enumerate(words):
            if 'year' in word or 'exp' in word:
                # Check previous and next words for numbers
                for j in range(max(0, i-3), min(len(words), i+4)):
                    try:
                        num = int(re.sub(r'[^\d]', '', words[j]))
                        if 0 < num < 50:
                            return num
                    except (ValueError, AttributeError):
                        continue
        
        return None
    
    def _extract_years_from_jd(self, jd_text: str) -> Optional[str]:
        """
        Extract years requirement from job description.
        
        Args:
            jd_text: Job description text
            
        Returns:
            Years requirement string (e.g., "3+ years", "5-7 years") or None
        """
        if not jd_text:
            return None
        
        jd_lower = jd_text.lower()
        
        # Patterns to match years requirements
        patterns = [
            r'(\d+)\s*(?:\+|-|to|-)\s*(\d+)?\s*years?\s+(?:of\s+)?(?:experience|exp)',
            r'(?:minimum|min|at least|atleast|required|require)\s+(\d+)\s*(?:\+)?\s*years?',
            r'(\d+)\s*(?:\+|-|to|-)\s*(\d+)?\s*years?\s+(?:in|of|with)',
            r'(\d+)\+?\s*years?',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, jd_lower)
            for match in matches:
                groups = match.groups()
                if groups[0]:
                    try:
                        years1 = int(groups[0])
                        if 0 < years1 < 50:
                            if groups[1]:
                                try:
                                    years2 = int(groups[1])
                                    return f"{years1}-{years2} years"
                                except (ValueError, IndexError):
                                    pass
                            return f"{years1}+ years" if '+' in match.group() else f"{years1} years"
                    except (ValueError, IndexError):
                        continue
        
        # Look for context around "years" keyword
        sentences = re.split(r'[.!?]', jd_lower)
        for sentence in sentences:
            if 'year' in sentence and ('experience' in sentence or 'exp' in sentence or 'required' in sentence or 'minimum' in sentence):
                # Extract numbers from this sentence
                numbers = re.findall(r'\d+', sentence)
                for num_str in numbers:
                    try:
                        num = int(num_str)
                        if 0 < num < 50:
                            return f"{num}+ years"
                    except ValueError:
                        continue
        
        return None
    
    def _calculate_with_rules(
        self, 
        scrubbed_resume: str, 
        job_description: str
    ) -> float:
        """
        Fallback rule-based calculation with improved years extraction.
        
        Args:
            scrubbed_resume: Resume text (scrubbed, no PII)
            job_description: Job description text
            
        Returns:
            Score from 0-100
        """
        try:
            # Parse resume and JD to extract skills
            resume_data = resume_parser.parse_resume(scrubbed_resume)
            jd_data = resume_parser.parse_jd(job_description)
            
            # Get skills
            resume_skills = set(resume_data.get("technologies", []))
            jd_skills = set(jd_data.get("technologies", []))
            jd_required_skills = set(jd_data.get("required_skills", []))
            
            # Calculate skill match (60% weight)
            skill_match_score = self._calculate_skill_match(
                resume_skills, 
                jd_skills, 
                jd_required_skills
            )
            
            # Calculate experience match with improved years extraction (30% weight)
            resume_years = resume_data.get("experience_years")
            if resume_years is None:
                # Try direct extraction
                resume_years = self._extract_years_from_text(scrubbed_resume)
            
            jd_years_required = self._extract_years_from_jd(job_description)
            experience_score = self._calculate_experience_match_improved(
                resume_years,
                jd_years_required,
                jd_data
            )
            
            # Calculate role relevance (10% weight)
            role_relevance_score = self._calculate_role_relevance(
                resume_data,
                jd_data
            )
            
            # Weighted final score
            final_score = (
                skill_match_score * 0.6 +
                experience_score * 0.3 +
                role_relevance_score * 0.1
            )
            
            # Ensure score is between 0-100
            return max(0.0, min(100.0, final_score))
            
        except Exception as e:
            logger.error(f"Error calculating resume score with rules: {str(e)}")
            return 0.0
    
    def _calculate_experience_match_improved(
        self,
        resume_years: Optional[int],
        jd_years_required: Optional[str],
        jd_data: Dict
    ) -> float:
        """
        Calculate experience match with explicit years comparison.
        
        Args:
            resume_years: Years of experience from resume
            jd_years_required: Years requirement string from JD (e.g., "3+ years", "5-7 years")
            jd_data: Parsed JD data
            
        Returns:
            Score from 0-100
        """
        if resume_years is None:
            return 50.0  # Default if experience not found
        
        # Parse JD years requirement
        jd_years_min = None
        jd_years_max = None
        
        if jd_years_required:
            # Extract numbers from requirement string
            numbers = re.findall(r'\d+', jd_years_required)
            if numbers:
                jd_years_min = int(numbers[0])
                if len(numbers) > 1:
                    jd_years_max = int(numbers[1])
                elif '+' in jd_years_required or 'minimum' in jd_years_required.lower() or 'at least' in jd_years_required.lower():
                    # It's a minimum requirement
                    jd_years_max = None
        
        # Compare years
        if jd_years_min is not None:
            if jd_years_max is not None:
                # Range requirement (e.g., "5-7 years")
                if jd_years_min <= resume_years <= jd_years_max:
                    return 100.0  # Perfect match
                elif resume_years > jd_years_max:
                    # Exceeds range - still good but slightly less ideal
                    excess = resume_years - jd_years_max
                    if excess <= 2:
                        return 95.0
                    elif excess <= 5:
                        return 85.0
                    else:
                        return 75.0  # Overqualified
                elif resume_years < jd_years_min:
                    # Below minimum
                    deficit = jd_years_min - resume_years
                    if deficit == 1:
                        return 70.0  # Close
                    elif deficit == 2:
                        return 55.0
                    else:
                        return 40.0  # Significantly below
            else:
                # Minimum requirement (e.g., "3+ years")
                if resume_years >= jd_years_min:
                    # Meets or exceeds
                    if resume_years == jd_years_min:
                        return 90.0
                    elif resume_years <= jd_years_min + 2:
                        return 95.0
                    elif resume_years <= jd_years_min + 5:
                        return 85.0
                    else:
                        return 75.0  # Overqualified
                else:
                    # Below minimum
                    deficit = jd_years_min - resume_years
                    if deficit == 1:
                        return 65.0  # Close
                    elif deficit == 2:
                        return 50.0
                    else:
                        return 35.0  # Significantly below
        
        # If no explicit years requirement, use heuristic
        jd_text = jd_data.get("scrubbed_text", "").lower()
        experience_keywords = [
            "years of experience", "years experience", 
            "minimum", "at least", "required"
        ]
        
        if any(keyword in jd_text for keyword in experience_keywords):
            # Assume 3-5 years is typical
            if 3 <= resume_years <= 5:
                return 100.0
            elif resume_years >= 5:
                return 90.0
            elif resume_years >= 2:
                return 70.0
            else:
                return 40.0
        
        # If no experience requirement mentioned, give moderate score
        return 60.0
    
    def _calculate_skill_match(
        self, 
        resume_skills: set, 
        jd_skills: set, 
        jd_required_skills: set
    ) -> float:
        """
        Calculate skill match percentage (fallback method).
        
        Args:
            resume_skills: Set of skills from resume
            jd_skills: Set of skills from JD
            jd_required_skills: Set of required skills from JD
            
        Returns:
            Score from 0-100
        """
        if not jd_skills and not jd_required_skills:
            return 50.0  # Default if no skills in JD
        
        # Combine all JD skills
        all_jd_skills = jd_skills.union(jd_required_skills)
        
        if not all_jd_skills:
            return 50.0
        
        # Calculate match
        matched_skills = resume_skills.intersection(all_jd_skills)
        match_percentage = (len(matched_skills) / len(all_jd_skills)) * 100
        
        # Bonus for required skills
        required_match = resume_skills.intersection(jd_required_skills)
        if jd_required_skills:
            required_bonus = (len(required_match) / len(jd_required_skills)) * 20
            match_percentage = min(100, match_percentage + required_bonus)
        
        return match_percentage
    
    def _calculate_experience_match(
        self, 
        resume_experience_years: Optional[int], 
        jd_data: Dict
    ) -> float:
        """
        Calculate experience match score (legacy fallback method).
        
        Args:
            resume_experience_years: Years of experience from resume
            jd_data: Parsed JD data
            
        Returns:
            Score from 0-100
        """
        if resume_experience_years is None:
            return 50.0  # Default if experience not found
        
        # Try to extract experience requirement from JD
        jd_text = jd_data.get("scrubbed_text", "").lower()
        jd_years_required = self._extract_years_from_jd(jd_text)
        
        return self._calculate_experience_match_improved(
            resume_experience_years,
            jd_years_required,
            jd_data
        )
    
    def _calculate_role_relevance(
        self, 
        resume_data: Dict, 
        jd_data: Dict
    ) -> float:
        """
        Calculate role relevance score (fallback method).
        
        Args:
            resume_data: Parsed resume data
            jd_data: Parsed JD data
            
        Returns:
            Score from 0-100
        """
        resume_areas = set(resume_data.get("areas", []))
        jd_role_type = jd_data.get("role_type", "").lower()
        
        # Map role types to areas
        role_area_mapping = {
            "genai engineer": ["machine_learning"],
            "java springboot": ["backend_development"],
            "python backend": ["backend_development"],
            "devops": ["devops", "cloud", "containerization"],
            "frontend": ["frontend_development"]
        }
        
        # Get expected areas for role
        expected_areas = set()
        for role, areas in role_area_mapping.items():
            if role in jd_role_type:
                expected_areas.update(areas)
        
        if not expected_areas:
            return 50.0  # Default if role not mapped
        
        # Calculate overlap
        overlap = resume_areas.intersection(expected_areas)
        relevance = (len(overlap) / len(expected_areas)) * 100 if expected_areas else 50.0
        
        return min(100.0, relevance)


# Global instance
resume_scorer = ResumeScorer()
