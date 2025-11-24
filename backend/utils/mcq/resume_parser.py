"""
Resume and Job Description Parser
Extracts skills and technologies after PII scrubbing
"""
from typing import Dict, List, Optional
from .pii_scrubber import pii_scrubber
from .domain_mapper import domain_mapper


class ResumeParser:
    """Parses resume and JD to extract relevant information"""
    
    def __init__(self):
        self.pii_scrubber = pii_scrubber
        self.domain_mapper = domain_mapper
    
    def scrub_and_extract_skills(self, text: str) -> Dict[str, any]:
        """
        Scrub PII and extract skills from text
        
        Args:
            text: Input text (resume or JD)
            
        Returns:
            Dictionary with scrubbed text and extracted skills
        """
        # Scrub PII first
        scrubbed_text = self.pii_scrubber.scrub_pii(text)
        
        # Validate no PII remains
        if not self.pii_scrubber.validate_no_pii(scrubbed_text):
            # If PII still detected, do more aggressive scrubbing
            scrubbed_text = self.pii_scrubber.scrub_pii(scrubbed_text)
        
        # Extract skills
        skills_data = self.pii_scrubber.extract_skills_only(scrubbed_text)
        
        return {
            "scrubbed_text": scrubbed_text,
            "skills": skills_data.get("technologies", []),
            "raw_skills_data": skills_data
        }
    
    def parse_resume(self, resume_text: str) -> Dict[str, any]:
        """
        Parse resume to extract skills and technologies
        
        Args:
            resume_text: Resume text (will be scrubbed)
            
        Returns:
            Dictionary with parsed resume data
        """
        # Scrub and extract
        parsed = self.scrub_and_extract_skills(resume_text)
        
        # Extract experience years (simple heuristic)
        scrubbed = parsed["scrubbed_text"].lower()
        experience_years = None
        for word in scrubbed.split():
            try:
                num = int(word)
                if num > 0 and num < 50:  # Reasonable range
                    # Check if followed by "year" or "years"
                    idx = scrubbed.find(word)
                    if idx != -1:
                        context = scrubbed[max(0, idx-10):min(len(scrubbed), idx+20)]
                        if "year" in context:
                            experience_years = num
                            break
            except ValueError:
                continue
        
        return {
            "technologies": parsed["skills"],
            "experience_years": experience_years,
            "scrubbed_text": parsed["scrubbed_text"],
            "areas": self._extract_areas(parsed["scrubbed_text"])
        }
    
    def parse_jd(self, jd_text: str) -> Dict[str, any]:
        """
        Parse job description to extract required skills and role type
        
        Args:
            jd_text: Job description text
            
        Returns:
            Dictionary with parsed JD data
        """
        # Scrub and extract (JD usually has less PII, but still scrub)
        parsed = self.scrub_and_extract_skills(jd_text)
        
        # Determine role type
        role_type = self.determine_role_type(jd_text)
        
        # Extract required skills (keywords that indicate requirements)
        scrubbed = parsed["scrubbed_text"].lower()
        required_keywords = [
            "required", "must have", "should have", "need", 
            "experience with", "knowledge of", "familiar with"
        ]
        
        required_skills = parsed["skills"].copy()
        
        return {
            "technologies": parsed["skills"],
            "required_skills": required_skills,
            "role_type": role_type,
            "scrubbed_text": parsed["scrubbed_text"]
        }
    
    def determine_role_type(self, jd_text: str) -> str:
        """
        Determine role type from JD
        
        Args:
            jd_text: Job description text
            
        Returns:
            Role type string
        """
        jd_lower = jd_text.lower()
        
        # Check for role keywords
        if any(keyword in jd_lower for keyword in ["genai", "generative ai", "llm", "transformer", "rag"]):
            return "GenAI Engineer"
        elif any(keyword in jd_lower for keyword in ["java springboot", "java spring boot", "java backend"]):
            return "Java Springboot"
        elif any(keyword in jd_lower for keyword in ["devops", "sre", "site reliability"]):
            return "DevOps"
        elif any(keyword in jd_lower for keyword in ["frontend", "front-end", "react", "vue", "angular"]):
            return "Frontend"
        else:
            # Default based on technologies mentioned
            if "java" in jd_lower and "spring" in jd_lower:
                return "Java Springboot"
            elif "python" in jd_lower:
                return "Python Backend"
            else:
                return "Unknown"
    
    def _extract_areas(self, text: str) -> List[str]:
        """
        Extract general areas of expertise from text
        
        Args:
            text: Scrubbed text
            
        Returns:
            List of areas
        """
        areas = []
        text_lower = text.lower()
        
        area_keywords = {
            "backend_development": ["backend", "server", "api", "microservices"],
            "frontend_development": ["frontend", "ui", "ux", "react", "vue", "angular"],
            "cloud": ["cloud", "aws", "azure", "gcp", "deployment"],
            "containerization": ["docker", "kubernetes", "container"],
            "devops": ["ci/cd", "pipeline", "jenkins", "gitlab", "terraform"],
            "database": ["database", "sql", "nosql", "mongodb", "postgresql"],
            "machine_learning": ["ml", "machine learning", "ai", "deep learning", "llm"]
        }
        
        for area, keywords in area_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                areas.append(area)
        
        return areas
    
    def combine_skills(self, resume_data: Dict, jd_data: Dict) -> List[str]:
        """
        Combine skills from resume and JD
        
        Args:
            resume_data: Parsed resume data
            jd_data: Parsed JD data
            
        Returns:
            Combined list of unique skills
        """
        all_skills = set()
        
        # Add resume skills
        all_skills.update(resume_data.get("technologies", []))
        
        # Add JD skills
        all_skills.update(jd_data.get("technologies", []))
        all_skills.update(jd_data.get("required_skills", []))
        
        # Return as sorted list
        return sorted(list(all_skills))


# Global instance
resume_parser = ResumeParser()

