"""
PII Detection and Scrubbing Module
Ensures no candidate personal information reaches the LLM
"""
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from typing import Dict, List


class PIIScrubber:
    """Handles PII detection and removal from text"""
    
    def __init__(self):
        """Initialize PII analyzer and anonymizer"""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
    def scrub_pii(self, text: str) -> str:
        """
        Remove all PII from text
        
        Args:
            text: Input text that may contain PII
            
        Returns:
            Text with PII replaced by placeholders
        """
        if not text or not isinstance(text, str):
            return text
        
        # Detect PII entities
        results = self.analyzer.analyze(text=text, language='en')
        
        # Anonymize detected PII
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )
        
        return anonymized.text
    
    def extract_skills_only(self, text: str) -> Dict[str, List[str]]:
        """
        Extract only technical skills/technologies from text (no personal info)
        
        Args:
            text: Input text (should be scrubbed first)
            
        Returns:
            Dictionary with extracted skills and technologies
        """
        # Common technology keywords
        tech_keywords = [
            'Java', 'Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#',
            'Spring Boot', 'Spring', 'Django', 'Flask', 'FastAPI', 'Express',
            'React', 'Vue', 'Angular', 'Node.js',
            'Microservices', 'REST', 'GraphQL', 'gRPC',
            'Docker', 'Kubernetes', 'Terraform', 'Ansible',
            'AWS', 'Azure', 'GCP', 'Cloud',
            'JPA', 'Hibernate', 'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL',
            'CI/CD', 'Jenkins', 'GitLab', 'GitHub Actions',
            'Machine Learning', 'Deep Learning', 'LLM', 'Transformer', 'RAG',
            'PyTorch', 'TensorFlow', 'HuggingFace', 'OpenAI',
            'Design Patterns', 'API design', 'System Design'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for keyword in tech_keywords:
            if keyword.lower() in text_lower:
                found_skills.append(keyword)
        
        return {
            "technologies": found_skills,
            "raw_text": text
        }
    
    def validate_no_pii(self, text: str) -> bool:
        """
        Verify no PII remains in text before sending to LLM
        
        Args:
            text: Text to validate
            
        Returns:
            True if no PII detected, False otherwise
        """
        if not text:
            return True
        
        results = self.analyzer.analyze(text=text, language='en')
        
        # Filter out only high-confidence PII (PERSON, EMAIL, PHONE, etc.)
        critical_entities = ['PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'LOCATION']
        critical_detections = [
            r for r in results 
            if r.entity_type in critical_entities and r.score > 0.7
        ]
        
        return len(critical_detections) == 0


# Global instance
pii_scrubber = PIIScrubber()

