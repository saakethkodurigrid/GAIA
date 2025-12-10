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
    
    async def calculate_score(
        self, 
        scrubbed_resume: str, 
        job_description: str,
        grade: Optional[str] = None,
        role_name: Optional[str] = None
    ) -> float:
        """
        Calculate resume score (0-100) based on match with job description using LLM.
        
        Uses scrubbed resume (no PII) for all calculations.
        
        Args:
            scrubbed_resume: Resume text with PII removed
            job_description: Job description text
            grade: Optional grade level (T2, T3, etc.) for role-specific evaluation
            role_name: Optional role name/title for role-specific experience evaluation
            
        Returns:
            Score from 0-100
        """
        if not scrubbed_resume or not job_description:
            return 0.0
        
        # Try LLM-based scoring first
        if self.llm:
            try:
                llm_score = await self._calculate_with_llm(
                    scrubbed_resume, 
                    job_description,
                    grade=grade,
                    role_name=role_name
                )
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
        job_description: str,
        grade: Optional[str] = None,
        role_name: Optional[str] = None
    ) -> Optional[float]:
        """
        Calculate single combined score using LLM with comprehensive multi-dimensional evaluation.
        
        Args:
            scrubbed_resume: Resume text (scrubbed, no PII)
            job_description: Job description text
            grade: Optional grade level (T2, T3, etc.) for role-specific evaluation
            role_name: Optional role name/title for role-specific experience evaluation
            
        Returns:
            Single combined score (0-100) or None if LLM call fails
        """
        from utils.grades import get_grade, format_grade_requirements
        
        # Build role context section
        role_context_text = ""
        if role_name:
            role_context_text = f"""

TARGET ROLE: {role_name}

The candidate is being evaluated for the role: **{role_name}**

ROLE-SPECIFIC EXPERIENCE EVALUATION:
- **CRITICAL**: Check if the candidate has direct experience in the same or very similar role (e.g., if role is "Senior Software Engineer", look for "Software Engineer", "Senior Developer", "Senior Engineer", etc.)
- If candidate has direct experience in the same/similar role: This is a STRONG POSITIVE indicator - add a bonus of +5 to +15 points to the overall score
- If candidate has experience in related roles but not the exact role: This is a MODERATE POSITIVE indicator - add a bonus of +2 to +8 points
- If candidate has no relevant role experience: This is a NEGATIVE indicator - reduce the score by -3 to -10 points
- Consider role progression (e.g., "Software Engineer" → "Senior Software Engineer" is positive)
- Consider role variations and synonyms (e.g., "Developer" = "Engineer", "Data Scientist" = "ML Engineer" in some contexts)

The role-specific experience should be evaluated in the EXPERIENCE RELEVANCE dimension and can influence the overall score adjustment.

"""
        
        # Get grade requirements if grade is provided
        grade_requirements_text = ""
        if grade:
            grade_data = get_grade(grade)
            if grade_data:
                grade_requirements_text = f"""

ROLE-SPECIFIC GRADE REQUIREMENTS:

The candidate is being evaluated for the {grade} position. In addition to the job description requirements, evaluate the candidate against the following company grade-specific requirements:

{format_grade_requirements(grade_data)}

IMPORTANT: When scoring, consider BOTH:
1. How well the candidate matches the job description requirements
2. How well the candidate meets the {grade} grade-specific requirements above

The grade requirements should influence your scoring, especially in:
- Experience Relevance dimension (check if candidate meets the grade's experience requirement - T2 requires 1+ years, T3 requires 3+ years)
- Technical Skills dimension (evaluate depth and breadth against grade expectations - T3 requires stronger expertise and architectural contributions)
- Soft Skills & Cultural Fit dimension (assess leadership, mentoring, communication per grade level - T3 requires stronger leadership and cross-functional communication)
- Role-Specific Achievements dimension (evaluate achievements against grade expectations - T3 requires more significant impact and innovation)

If the candidate significantly falls short of grade requirements, this should negatively impact the overall score. Conversely, if the candidate exceeds grade requirements, this should positively impact the score.

"""
        
        prompt = f"""ROLE DEFINITION:

You are an expert AI recruitment analyst specializing in candidate-job fit assessment for the Indian market. Your task is to evaluate how well a candidate's resume matches a specific job description using a structured, multi-factor scoring methodology.
{role_context_text}
EVALUATION FRAMEWORK:

Analyze the following resume against the provided job description and generate a comprehensive matching score across five critical dimensions:
{grade_requirements_text}
INPUT FORMAT:

- TARGET ROLE: {role_name if role_name else "Not specified"}
- JOB DESCRIPTION: [Provided below]
- RESUME: [Provided below - PII removed]

SCORING METHODOLOGY:

1. HARD SKILLS MATCH (Weight: 30%)
   - Extract required technical skills, tools, software, frameworks, programming languages, and certifications from the job description
   - Map explicitly stated skills in the resume
   - Consider both exact matches and related/equivalent technologies (e.g., React and Vue.js are related frontend frameworks)
   - Score: 0-100 based on percentage of required skills present
   - Apply penalty: -5 points per critical missing skill that is explicitly required
   - Weight required skills more heavily than preferred/nice-to-have skills

2. EXPERIENCE RELEVANCE (Weight: 25%)
   - **CRITICAL**: Extract the exact years of experience requirement from the JD (e.g., "3+ years", "5-7 years", "minimum 2 years", "at least 4 years")
   - **CRITICAL**: Extract the candidate's total years of experience from the resume
   - **ROLE-SPECIFIC EXPERIENCE**: Check if candidate has direct experience in the same or similar role as the target role. This is a KEY factor:
     * If candidate has direct experience in the same/similar role: This significantly strengthens their profile - score 85-100 for this dimension
     * If candidate has experience in related roles: Score 70-84
     * If candidate has no relevant role experience: Score 50-69 (even if they have relevant skills/experience in other areas)
   - Compare candidate's years with JD requirement:
     * If candidate meets or exceeds requirement: Strong positive score (85-100)
     * If candidate is close (within 1-2 years): Moderate positive score (70-84)
     * If candidate is below requirement: Negative impact (more negative if significantly below)
   - Assess industry/domain alignment (e.g., fintech, e-commerce, healthcare)
   - Evaluate seniority level match (junior, mid-level, senior, lead)
   - Consider quality and relevance of work experience, not just duration
   - Score: 0-100 based on alignment and depth, with role-specific experience being a major factor

3. SOFT SKILLS & CULTURAL FIT (Weight: 20%)
   - Identify implied soft skills from JD language (e.g., "collaborative", "self-starter", "leadership", "communication")
   - Match with demonstrated examples in resume (e.g., "led a team", "collaborated with cross-functional teams")
   - Look for evidence of: teamwork, leadership, problem-solving, communication, adaptability, ownership
   - Score: 0-100 based on evidence quality and alignment with JD expectations

4. EDUCATION & CREDENTIALS (Weight: 15%)
   - Verify required degrees/certifications match JD requirements
   - Assess relevance of educational background to the role
   - Consider prestige/relevance of institutions (for Indian context: IITs, NITs, tier-1 colleges vs. others)
   - Evaluate professional certifications and their relevance
   - Score: 0-100 based on requirements met and relevance

5. ROLE-SPECIFIC ACHIEVEMENTS (Weight: 10%)
   - Quantify achievements matching JD priorities (e.g., "improved performance by X%", "led team of Y", "reduced costs by Z")
   - Assess impact metrics and their relevance to the role
   - Evaluate project complexity and outcomes
   - Consider awards, recognitions, publications if relevant
   - Score: 0-100 based on achievement quality and relevance

CALCULATION FORMULA:

BASE OVERALL MATCH SCORE = Σ(Dimension Score × Weight) / 100

ROLE-SPECIFIC EXPERIENCE ADJUSTMENT:
- If candidate has direct experience in same/similar role: +5 to +15 points
- If candidate has experience in related roles: +2 to +8 points  
- If candidate has no relevant role experience: -3 to -10 points

FINAL OVERALL MATCH SCORE = BASE SCORE + ROLE-SPECIFIC EXPERIENCE ADJUSTMENT (capped at 0-100)

**Resume (PII removed):**
```
{scrubbed_resume}
```

**Job Description:**
```
{job_description}
```

OUTPUT REQUIREMENTS:

Provide your analysis in this exact JSON format:

{{
  "overall_match_score": 0-100,
  "base_score": 0-100,
  "role_experience_adjustment": -10 to +15,
  "role_experience_assessment": "direct_match|related_experience|no_relevant_experience",
  "dimension_scores": {{
    "hard_skills_match": {{"score": 0-100, "weight": 0.30, "rationale": "2-3 sentence explanation with specific evidence from resume"}},
    "experience_relevance": {{"score": 0-100, "weight": 0.25, "rationale": "2-3 sentence explanation including years comparison, role-specific experience assessment, and domain alignment"}},
    "soft_skills_cultural_fit": {{"score": 0-100, "weight": 0.20, "rationale": "2-3 sentence explanation with demonstrated examples"}},
    "education_credentials": {{"score": 0-100, "weight": 0.15, "rationale": "2-3 sentence explanation of educational alignment"}},
    "role_specific_achievements": {{"score": 0-100, "weight": 0.10, "rationale": "2-3 sentence explanation of relevant achievements"}}
  }},
  "key_strengths": ["strength1", "strength2", "strength3"],
  "critical_gaps": [{{"gap": "description of gap", "impact": "high|medium|low"}}],
  "recommendation": "STRONG_MATCH|MODERATE_MATCH|WEAK_MATCH",
  "confidence_level": "high|medium|low"
}}

SCORING NORMALIZATION:

- 90-100: Exceptional match - candidate strongly meets or exceeds all requirements, including role-specific experience
- 75-89: Strong match - candidate meets most requirements well, with relevant role experience
- 60-74: Moderate match - candidate meets core requirements, some gaps, may lack direct role experience
- 40-59: Weak match - candidate has limited relevant experience, likely lacks role-specific experience
- 0-39: Poor fit - candidate does not meet most requirements and lacks relevant role experience

CONFIDENCE LEVEL DETERMINANTS:

HIGH CONFIDENCE (>90%):
- Complete information in both JD and resume
- Clear skill statements with proficiency levels
- Quantified achievements
- Standard formatting
- Clear role titles in resume matching target role

MEDIUM CONFIDENCE (70-89%):
- Some ambiguous statements
- Missing proficiency indicators
- Non-standard section headers
- Industry jargon variations
- Unclear role title matches

LOW CONFIDENCE (<70%):
- Significant information gaps
- Unparsed formatting issues
- Vague accomplishment descriptions
- Contradictory timeline information

BIAS PREVENTION PROTOCOL:

- Ignore candidate name, gender indicators, age, ethnicity
- Focus solely on skills, experience, and achievements
- Do not penalize employment gaps without JD context
- Evaluate alternative experience paths equally (e.g., freelancing, startups, consulting)
- Standardize scoring regardless of resume formatting quality

ADDITIONAL INSTRUCTIONS:

- Be objective and data-driven in your assessment
- Provide specific evidence from the resume to support each score
- Flag any ambiguity or missing information that affects confidence
- Consider both explicit requirements and implied needs from the JD
- For Indian market context: Consider tier-1/tier-2 college distinctions, startup vs. enterprise experience, and relevant certifications
- Base all scores on actual content, not assumptions
- Ensure all dimension scores are within 0-100 range
- Ensure weights sum to 1.0 (100%)
- **CRITICALLY**: Evaluate role-specific experience carefully - this is a key differentiator for candidate fit
- When assessing role experience, consider variations, synonyms, and role progression (e.g., Junior → Senior, Engineer → Lead Engineer)

Respond with ONLY the JSON object, no additional text."""

        try:
            messages = [
                LLMMessage(
                    role="system",
                    content="You are an expert AI recruitment analyst specializing in candidate-job fit assessment. Always respond with valid JSON only. Provide a comprehensive multi-dimensional evaluation with overall_match_score as the primary metric. Pay special attention to role-specific experience when evaluating candidates."
                ),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=2000  # Increased for comprehensive response
            )
            
            content = response.content.strip()
            
            # Extract JSON if wrapped in code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            result = json.loads(content)
            
            # Extract overall_match_score (with backward compatibility for old "score" key)
            score = float(result.get("overall_match_score", result.get("score", 0)))
            
            # Ensure score is in valid range
            score = max(0.0, min(100.0, score))
            
            # Log additional details if available
            if "dimension_scores" in result:
                logger.info(f"LLM Overall Match Score: {score:.1f}")
                if "role_experience_assessment" in result:
                    logger.info(f"Role Experience: {result.get('role_experience_assessment')}, Adjustment: {result.get('role_experience_adjustment', 0)}")
                logger.debug(f"Dimension scores: {result.get('dimension_scores')}")
                logger.debug(f"Recommendation: {result.get('recommendation')}, Confidence: {result.get('confidence_level')}")
            else:
                logger.info(f"LLM Combined Score: {score:.1f}")
            
            return score
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}. Content: {content[:200]}")
            return None
        except KeyError as e:
            logger.error(f"Missing 'overall_match_score' or 'score' key in LLM response: {e}. Response: {result}")
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
