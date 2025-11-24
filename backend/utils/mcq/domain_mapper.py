"""
Domain Mapping and Subtopics Module
Maps roles to domains and provides relevant subtopics
"""
from typing import List, Dict, Optional


class DomainMapper:
    """Maps roles to domains and manages subtopics"""
    
    # Domain to question range mapping
    DOMAIN_RANGES = {
        "genAI": (1, 150),
        "java": (151, 300),
        "python_backend": (301, 420),
        "java_backend": (421, 570),
        "cloud": (571, None)  # None means end of file
    }
    
    # Role to domain mapping
    ROLE_TO_DOMAIN = {
        "GenAI": "genAI",
        "GenAI Engineer": "genAI",
        "Generative AI": "genAI",
        "Java Springboot": "java_backend",
        "Java Spring Boot": "java_backend",
        "Java Backend": "java_backend",
        "Frontend": None,  # No domain match, generate without RAG
        "DevOps": "cloud",
        "DevOps Engineer": "cloud",
        "SRE": "cloud"
    }
    
    # Subtopics by domain
    SUBTOPICS = {
        "java_backend": [
            "Design Patterns",
            "API design",
            "Java Core",
            "Spring boot",
            "Microservices",
            "JPA/Hibernate",
            "Unit/Integration testing",
            "System Design",
            "CI/CD",
            "Containerisation",
            "Cloud"
        ],
        "genAI": [
            "Machine Learning & Deep Learning Foundations",
            "Transformer Architecture",
            "Large Language Models (LLMs)",
            "Foundation Model Ecosystem (HuggingFace, OpenAI, vLLM, etc.)",
            "Retrieval-Augmented Generation (RAG)",
            "Fine-Tuning & Custom Model Training (LoRA, QLoRA, PEFT)",
            "Multimodal AI (Vision, Audio, Speech)",
            "MLOps for GenAI",
            "Vector Databases & Indexing",
            "Cloud Platforms for GenAI",
            "Security, Safety & Compliance (Prompt Injection, Responsible AI)",
            "System Design for GenAI Applications",
            "AI Agents & Tool-Use",
            "Python for GenAI (PyTorch, FastAPI, etc.)",
            "Containerisation & CI/CD for AI",
            "Advanced NLP (RLHF, DPO, Tokenization, Interpretability)"
        ],
        "cloud": [
            "Linux & Shell Scripting & Linux Troubleshooting / OS patching",
            "Version Control",
            "CI/CD Pipelines",
            "Python Language specific questions - basic knowledge of python",
            "Containers & Container Orchestration - Docker / Kubernetes",
            "Terraform / IAAC",
            "Cloud Platforms",
            "Networking Fundamentals",
            "Monitoring & Logging",
            "Configuration Management / Ansible / any other",
            "Security & Compliance",
            "Microservices Deployment & Management",
            "Artifact Management",
            "Container Networking & Service Mesh",
            "Scalability & High Availability",
            "Cost Optimization & Resource Management",
            "SRE Concepts",
            "Kubernetes Ecosystem Tools"
        ],
        "java": [
            "Java Core",
            "OOP Concepts",
            "Collections",
            "Concurrency",
            "Memory Management",
            "Exceptions",
            "Generics",
            "Streams API",
            "Lambda Expressions",
            "Design Patterns"
        ],
        "python_backend": [
            "Python Core",
            "Django",
            "Flask",
            "FastAPI",
            "REST APIs",
            "Database Integration",
            "Async Programming",
            "Testing",
            "Deployment",
            "Microservices"
        ]
    }
    
    def get_domain_for_role(self, role: str) -> Optional[str]:
        """
        Map role to domain
        
        Args:
            role: Role name (e.g., "Java Springboot", "GenAI Engineer")
            
        Returns:
            Domain name or None if no match
        """
        # Normalize role name
        role_normalized = role.strip()
        
        # Direct lookup
        if role_normalized in self.ROLE_TO_DOMAIN:
            return self.ROLE_TO_DOMAIN[role_normalized]
        
        # Fuzzy matching
        role_lower = role_normalized.lower()
        for role_key, domain in self.ROLE_TO_DOMAIN.items():
            if role_key.lower() in role_lower or role_lower in role_key.lower():
                return domain
        
        return None
    
    def get_subtopics_for_domain(self, domain: str) -> List[str]:
        """
        Get all subtopics for a domain
        
        Args:
            domain: Domain name
            
        Returns:
            List of subtopics
        """
        return self.SUBTOPICS.get(domain, [])
    
    def get_relevant_subtopics(
        self, 
        jd_text: str, 
        resume_text: str, 
        domain: str
    ) -> List[str]:
        """
        Determine which subtopics are relevant based on JD/resume content
        
        Args:
            jd_text: Job description text (scrubbed)
            resume_text: Resume text (scrubbed)
            domain: Domain name
            
        Returns:
            List of relevant subtopics
        """
        all_subtopics = self.get_subtopics_for_domain(domain)
        if not all_subtopics:
            return []
        
        # Combine texts for analysis
        combined_text = (jd_text + " " + resume_text).lower()
        
        relevant = []
        for subtopic in all_subtopics:
            # Check if subtopic keywords appear in text
            subtopic_keywords = subtopic.lower().split()
            # Check if any significant keyword from subtopic is in text
            for keyword in subtopic_keywords:
                # Skip common words
                if keyword in ['and', 'or', 'the', 'for', 'etc', 'etc.']:
                    continue
                if len(keyword) > 3 and keyword in combined_text:
                    relevant.append(subtopic)
                    break
        
        # If no matches found, return top 5-8 most important subtopics
        if not relevant:
            # Return first few subtopics as defaults
            return all_subtopics[:8] if len(all_subtopics) > 8 else all_subtopics
        
        # Remove duplicates while preserving order
        seen = set()
        unique_relevant = []
        for item in relevant:
            if item not in seen:
                seen.add(item)
                unique_relevant.append(item)
        
        return unique_relevant
    
    def get_domain_range(self, domain: str) -> tuple:
        """
        Get question ID range for a domain
        
        Args:
            domain: Domain name
            
        Returns:
            Tuple of (start_id, end_id) or None
        """
        return self.DOMAIN_RANGES.get(domain, (None, None))


# Global instance
domain_mapper = DomainMapper()

