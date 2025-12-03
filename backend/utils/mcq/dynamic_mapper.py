"""
Dynamic Domain and Subtopic Mapping using LLM
Handles any role name and intelligently maps to domains/subtopics
"""
from typing import List, Dict, Optional
import json
import re
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage
from core.config import settings
from .domain_mapper import domain_mapper


class DynamicMapper:
    """Uses LLM to dynamically map roles and identify subtopics"""
    
    def __init__(self):
        """Initialize dynamic mapper with LLM provider"""
        self.domain_mapper = domain_mapper
        
        # Use factory to get LLM provider with configured model
        try:
            self.llm = LLMProviderFactory.create_provider()
            self.model = self.llm.model  # Store the actual model being used
        except ValueError as e:
            raise ValueError(f"{str(e)}. Please set LLM_PROVIDER and API key in your .env file.")
        
        # Available domains (for LLM reference)
        self.available_domains = {
            "genAI": "Generative AI, LLMs, Transformers, RAG, Fine-tuning, AI Agents, Multimodal AI",
            "java_backend": "Java, Spring Boot, Microservices, JPA, Hibernate, REST APIs, Design Patterns",
            "python_backend": "Python, Django, Flask, FastAPI, Backend Development, REST APIs",
            "java": "Java Core, OOP, Collections, Concurrency, Memory Management",
            "cloud": "DevOps, Docker, Kubernetes, Terraform, CI/CD, Cloud Platforms, SRE, Infrastructure"
        }
    
    async def map_role_to_domain(
        self, 
        role: str, 
        jd_text: str, 
        resume_text: str
    ) -> Optional[str]:
        """
        Use LLM to dynamically map any role name to domain
        
        Args:
            role: Role name (can be anything: "AI Engineer", "ML Engineer", etc.)
            jd_text: Full job description (scrubbed, not truncated)
            resume_text: Full resume (scrubbed, not truncated)
            
        Returns:
            Domain name or None if cannot determine
        """
        prompt = f"""You are a domain classifier for technical roles.

Available domains and their focus areas:
1. genAI - Generative AI, LLMs, Transformers, RAG, Fine-tuning, AI Agents, Multimodal AI, MLOps for AI
2. java_backend - Java, Spring Boot, Microservices, JPA, Hibernate, REST APIs, Design Patterns, System Design
3. python_backend - Python, Django, Flask, FastAPI, Backend Development, REST APIs, Database Integration
4. java - Java Core, OOP, Collections, Concurrency, Memory Management (general Java programming)
5. cloud - DevOps, Docker, Kubernetes, Terraform, CI/CD, Cloud Platforms, SRE, Infrastructure as Code

Role Name: {role}

Job Description:
{jd_text}

Resume Context:
{resume_text}

Based on the role name, job description, and resume context, determine which domain best matches this role.

Consider:
- Primary technologies and frameworks mentioned
- Main responsibilities and focus areas
- Experience and expertise described

Respond with ONLY the domain name (genAI, java_backend, python_backend, java, or cloud).
If the role doesn't clearly fit any domain, respond with "unknown".

Domain:"""
        
        try:
            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=50
            )
            
            domain = response.content.strip().lower()
            
            # Clean up response (remove any extra text)
            domain = domain.split()[0] if domain.split() else domain
            domain = domain.replace(".", "").replace(",", "").strip()
            
            # Validate domain and normalize to match tool schema
            valid_domains_lower = ["genai", "java_backend", "python_backend", "java", "cloud"]
            domain_mapping = {
                "genai": "genAI",  # Map to tool schema format
                "java_backend": "java_backend",
                "python_backend": "python_backend",
                "java": "java",
                "cloud": "cloud"
            }
            final_domain = None
            domain_lower = domain.lower()
            
            if domain_lower in valid_domains_lower:
                final_domain = domain_mapping.get(domain_lower, domain)
            elif domain == "unknown":
                # Try fallback to keyword matching
                fallback = self.domain_mapper.get_domain_for_role(role)
                final_domain = domain_mapping.get(fallback.lower(), fallback) if fallback else None
            else:
                # Try fuzzy match
                for valid_lower in valid_domains_lower:
                    if valid_lower in domain_lower or domain_lower in valid_lower:
                        final_domain = domain_mapping.get(valid_lower, domain)
                        break
                if not final_domain:
                    # Final fallback
                    fallback = self.domain_mapper.get_domain_for_role(role)
                    final_domain = domain_mapping.get(fallback.lower(), fallback) if fallback else None
            
            return final_domain
                
        except Exception as e:
            print(f"Error in LLM domain mapping: {e}, using fallback")
            # Fallback to keyword matching
            return self.domain_mapper.get_domain_for_role(role)
    
    async def identify_relevant_subtopics(
        self,
        domain: str,
        jd_text: str,
        resume_text: str
    ) -> List[str]:
        """
        Use LLM to identify relevant subtopics from the domain's subtopic list
        
        Args:
            domain: Domain name
            jd_text: Full job description (scrubbed, not truncated)
            resume_text: Full resume (scrubbed, not truncated)
            
        Returns:
            List of relevant subtopics
        """
        all_subtopics = self.domain_mapper.get_subtopics_for_domain(domain)
        if not all_subtopics:
            return []
        
        # Format subtopics for LLM
        subtopics_list = "\n".join([f"{i+1}. {st}" for i, st in enumerate(all_subtopics)])
        
        prompt = f"""You are analyzing a job description and resume to identify relevant technical subtopics for generating assessment questions.

Domain: {domain}

Available Subtopics for this domain:
{subtopics_list}

Job Description:
{jd_text}

Resume Context:
{resume_text}

Based on the job description and resume, identify which subtopics are MOST RELEVANT and IMPORTANT for generating assessment questions for this candidate.

Consider:
- What technologies and concepts are explicitly mentioned?
- What areas of expertise are emphasized?
- What responsibilities and requirements are described?
- What experience does the candidate have?

Select 8-12 most relevant subtopics that should be covered in the assessment.

Respond with a JSON array of the subtopic numbers that are relevant (e.g., [1, 3, 5, 7, 9, 11, 13, 15]).
Only include subtopics that are clearly mentioned or strongly implied in the JD/resume.

JSON array:"""
        
        try:
            messages = [
                LLMMessage(role="system", content="You are a technical assessment assistant. Always respond with valid JSON only. Return a JSON array of numbers representing relevant subtopic indices."),
                LLMMessage(role="user", content=prompt)
            ]
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.4,
                max_tokens=200
            )
            
            # Check if response has content
            if not response or not response.content:
                print("Error in LLM subtopic identification: Empty response from LLM, using fallback")
                return self.domain_mapper.get_relevant_subtopics(
                    jd_text, resume_text, domain
                )
            
            content = response.content.strip()
            
            # Check if content is empty after stripping
            if not content:
                print("Error in LLM subtopic identification: Empty content after stripping, using fallback")
                return self.domain_mapper.get_relevant_subtopics(
                    jd_text, resume_text, domain
                )
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to find JSON array in content if not already extracted
            json_match = re.search(r'\[[\d\s,]+\]', content)
            if json_match:
                content = json_match.group(0)
            
            # Check again if content is empty
            if not content:
                print(f"Error in LLM subtopic identification: Could not extract JSON from response: {response.content[:200]}, using fallback")
                return self.domain_mapper.get_relevant_subtopics(
                    jd_text, resume_text, domain
                )
            
            # Parse indices
            indices = json.loads(content)
            
            # Ensure it's a list
            if not isinstance(indices, list):
                indices = [indices]
            
            # Map indices to subtopics (indices are 1-based)
            relevant = []
            for i in indices:
                try:
                    idx = int(i) - 1  # Convert to 0-based
                    if 0 <= idx < len(all_subtopics):
                        relevant.append(all_subtopics[idx])
                except (ValueError, TypeError):
                    # Skip invalid indices
                    continue
            
            # Remove duplicates while preserving order
            seen = set()
            unique_relevant = []
            for st in relevant:
                if st not in seen:
                    seen.add(st)
                    unique_relevant.append(st)
            
            # Limit to 12
            final_subtopics = unique_relevant[:12]
            
            # If we got no valid subtopics, use fallback
            if not final_subtopics:
                print(f"Error in LLM subtopic identification: No valid subtopics extracted from response: {content[:200]}, using fallback")
                return self.domain_mapper.get_relevant_subtopics(
                    jd_text, resume_text, domain
                )
            
            return final_subtopics
            
        except json.JSONDecodeError as e:
            print(f"Error in LLM subtopic identification: JSON decode error: {e}")
            if 'response' in locals() and response and response.content:
                print(f"Response content: {response.content[:200]}")
            print("Using fallback")
            # Fallback to keyword matching
            return self.domain_mapper.get_relevant_subtopics(
                jd_text, resume_text, domain
            )
        except Exception as e:
            print(f"Error in LLM subtopic identification: {e}, using fallback")
            if 'response' in locals() and response and response.content:
                print(f"Response content: {response.content[:200] if response.content else 'None'}")
            # Fallback to keyword matching
            return self.domain_mapper.get_relevant_subtopics(
                jd_text, resume_text, domain
            )


# Global instance (lazy initialization)
dynamic_mapper = None

def get_dynamic_mapper() -> DynamicMapper:
    """Get or create dynamic mapper instance"""
    global dynamic_mapper
    if dynamic_mapper is None:
        dynamic_mapper = DynamicMapper()
    return dynamic_mapper

