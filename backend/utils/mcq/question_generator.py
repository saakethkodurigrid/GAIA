"""
Question Generator using Groq LLM
Generates MCQ questions based on RAG examples and requirements
"""
import json
import time
from typing import List, Dict, Optional, Any
from groq import Groq
from core.config import settings
from services.mcq_rag_service import rag_system
from .rag_tool import get_rag_tool_definition, execute_rag_tool_call
from .domain_mapper import domain_mapper
import numpy as np
from sentence_transformers import SentenceTransformer


class QuestionGenerator:
    """Generates MCQ questions using Groq LLM with RAG"""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize question generator
        
        Args:
            groq_api_key: Groq API key (if None, reads from settings)
        """
        self.api_key = groq_api_key or settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables. Please set GROQ_API_KEY in your .env file.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # or "mixtral-8x7b-32768"
        self.embedding_model = None  # For deduplication
    
    def _load_embedding_model(self):
        """Load embedding model for deduplication"""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
    
    def _calculate_difficulty_distribution(self, grade: str, total: int = 25) -> Dict[str, int]:
        """
        Calculate difficulty distribution based on grade
        
        Args:
            grade: Grade level (T2 or T3)
            total: Total number of questions
            
        Returns:
            Dictionary with difficulty counts
        """
        # Both T2 and T3: 60% hard, 30% medium, 10% easy
        hard_count = int(total * 0.6)
        medium_count = int(total * 0.3)
        easy_count = total - hard_count - medium_count
        
        return {
            "hard": hard_count,
            "medium": medium_count,
            "easy": easy_count
        }
    
    def _format_example_question(self, question: Dict[str, Any]) -> str:
        """
        Format a question for inclusion in prompt
        
        Args:
            question: Question dictionary
            
        Returns:
            Formatted string
        """
        return f"""Question: {question.get('question', '')}
Options:
1. {question.get('option1', '')}
2. {question.get('option2', '')}
3. {question.get('option3', '')}
4. {question.get('option4', '')}
Correct Answer: {question.get('correct_option', 1)}
Tags: {', '.join(question.get('tags', []))}"""
    
    def _create_agentic_prompt(
        self,
        role: str,
        domain: str,
        difficulty: str,
        grade: str,
        subtopics: List[str],
        skills: List[str],
        resume_text: str,
        jd_text: str,
        count: int
    ) -> str:
        """
        Create prompt for agentic question generation with tool calling
        
        Args:
            role: Role name
            domain: Domain name
            difficulty: Difficulty level
            grade: Grade level
            subtopics: Relevant subtopics
            skills: Required skills
            resume_text: Full scrubbed resume text
            jd_text: Full scrubbed JD text
            count: Number of questions to generate
            
        Returns:
            System prompt string
        """
        # Normalize domain for tool schema (genai -> genAI)
        domain_mapping = {
            "genai": "genAI",
            "java_backend": "java_backend",
            "python_backend": "python_backend",
            "java": "java",
            "cloud": "cloud"
        }
        normalized_domain = domain_mapping.get(domain.lower(), domain)
        
        subtopics_text = "\n".join([f"- {st}" for st in subtopics]) if subtopics else "General topics in the domain"
        skills_text = ", ".join(skills) if skills else "General skills"
        
        prompt = f"""You are an expert MCQ question generator for technical assessments.

Your task: Generate {count} NEW multiple-choice questions for a {difficulty} difficulty level ({grade} grade).

Role: {role}
Domain: {normalized_domain}
Difficulty: {difficulty} ({grade} level, requires {'deep understanding' if difficulty == 'hard' else 'moderate understanding' if difficulty == 'medium' else 'basic understanding'})

Candidate Background (PII removed):
{resume_text}

Job Requirements (PII removed):
{jd_text}

Relevant Subtopics to Cover:
{subtopics_text}

Key Skills: {skills_text}

You have access to a tool called `search_question_database` that lets you search for example questions from our dataset. 

WORKFLOW:
1. Use the `search_question_database` tool to find example questions for inspiration. You can call it multiple times with different queries to explore different subtopics.
2. Analyze the example questions to understand the style, difficulty level, and topic coverage.
3. Generate {count} COMPLETELY NEW questions that:
   - Match the {difficulty} difficulty level
   - Cover topics from the relevant subtopics
   - Test knowledge relevant to the candidate's background and job requirements
   - Are NOT duplicates of the examples (use them only for inspiration)
   - Follow the exact JSON format specified below

IMPORTANT:
- DO NOT duplicate any questions from the examples
- Use examples only for understanding style and difficulty
- Generate questions that are relevant to the candidate's experience and the job requirements
- Ensure questions test practical knowledge at the {difficulty} level

Output Format (JSON array of {count} questions):
{{
  "question": "Question text here?",
  "option1": "Option 1",
  "option2": "Option 2",
  "option3": "Option 3",
  "option4": "Option 4",
  "correct_option": 2,
  "difficulty": "{difficulty}",
  "tags": ["Tag1", "Tag2"]
}}

Start by searching the database for relevant examples, then generate the questions."""
        
        return prompt
    
    def _create_prompt(
        self,
        role: str,
        domain: str,
        difficulty: str,
        grade: str,
        subtopics: List[str],
        skills: List[str],
        resume_text: str,
        jd_text: str,
        example_questions: List[Dict[str, Any]],
        count: int
    ) -> str:
        """
        Create prompt for Groq LLM with full context
        
        Args:
            role: Role name
            domain: Domain name
            difficulty: Difficulty level
            grade: Grade level
            subtopics: Relevant subtopics
            skills: Required skills (for reference)
            resume_text: Full scrubbed resume text
            jd_text: Full scrubbed job description text
            example_questions: Example questions from RAG
            count: Number of questions to generate
            
        Returns:
            Prompt string
        """
        examples_text = ""
        if example_questions:
            examples_text = "\n\nExample questions from our dataset (for inspiration only, DO NOT duplicate these exact questions):\n\n"
            for i, ex_q in enumerate(example_questions[:5], 1):
                examples_text += f"{i}. {self._format_example_question(ex_q)}\n\n"
        else:
            examples_text = "\n\nNote: No similar questions found in dataset. Generate questions based on the requirements below.\n\n"
        
        subtopics_text = "\n".join([f"- {st}" for st in subtopics]) if subtopics else "General topics in the domain"
        skills_text = ", ".join(skills) if skills else "General skills"
        
        prompt = f"""You are generating MCQ questions for a technical assessment.

Role: {role}
Domain: {domain}
Difficulty: {difficulty}
Grade Level: {grade}

Candidate Background (PII removed):
{resume_text}

Job Requirements (PII removed):
{jd_text}

Relevant Subtopics to Cover:
{subtopics_text}

Key Skills Identified: {skills_text}
{examples_text}
Generate {count} NEW multiple-choice questions that:
1. Match the difficulty level: {difficulty} ({grade} level, requires {'deep understanding' if difficulty == 'hard' else 'moderate understanding' if difficulty == 'medium' else 'basic understanding'})
2. Cover topics from the relevant subtopics list above
3. Test knowledge relevant to the candidate's background and job requirements
4. Consider the candidate's experience level and expertise areas mentioned in their background
5. Are COMPLETELY NEW and not duplicates of the examples above
6. Follow this exact JSON format:
{{
  "question": "Question text here?",
  "option1": "Option 1",
  "option2": "Option 2",
  "option3": "Option 3",
  "option4": "Option 4",
  "correct_option": 2,
  "difficulty": "{difficulty}",
  "tags": ["Tag1", "Tag2"]
}}

Output only a valid JSON array of {count} question objects. No other text. Ensure the JSON is valid and parseable."""
        
        return prompt
    
    def _generate_questions_agentic(
        self,
        system_prompt: str,
        difficulty: str,
        domain: str,
        max_iterations: int = 10,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using agentic approach with function calling
        
        Args:
            system_prompt: System prompt for the LLM
            difficulty: Difficulty level
            domain: Domain name
            max_iterations: Maximum number of tool call iterations
            max_retries: Maximum retries for API calls
            
        Returns:
            List of generated questions
        """
        # Get RAG tool definition
        rag_tool = get_rag_tool_definition()
        tools = [rag_tool]
        
        # Initialize conversation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please start by searching the database for relevant example questions, then generate the required questions."}
        ]
        
        tool_calls_count = 0
        questions = []
        
        for iteration in range(max_iterations):
            try:
                # Call Groq API with function calling
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",  # Let LLM decide when to use tools
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=4000
                )
                
                message = response.choices[0].message
                
                # Add assistant message to conversation
                messages.append(message)
                
                # Check if LLM wants to call a tool
                if message.tool_calls:
                    # Execute tool calls
                    for tool_call in message.tool_calls:
                        tool_calls_count += 1
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Execute tool call
                        if function_name == "search_question_database":
                            # Normalize domain to match tool schema (genai -> genAI)
                            tool_domain = function_args.get("domain", domain)
                            domain_mapping = {
                                "genai": "genAI",
                                "java_backend": "java_backend",
                                "python_backend": "python_backend",
                                "java": "java",
                                "cloud": "cloud"
                            }
                            normalized_domain = domain_mapping.get(tool_domain.lower(), tool_domain)
                            
                            tool_result = execute_rag_tool_call(
                                query_text=function_args.get("query_text", ""),
                                difficulty=function_args.get("difficulty", difficulty),
                                domain=normalized_domain,
                                top_k=function_args.get("top_k", 10)
                            )
                            
                            # Format tool result for LLM
                            tool_result_text = f"""Tool call result:
Found {tool_result['count']} similar questions.

Example questions (for inspiration only, DO NOT duplicate):
"""
                            for i, q in enumerate(tool_result['questions'][:5], 1):
                                tool_result_text += f"""
{i}. {q['question']}
   Options: {q['options'][0]}, {q['options'][1]}, {q['options'][2]}, {q['options'][3]}
   Correct: Option {q['correct_option']}
   Tags: {', '.join(q.get('tags', []))}
"""
                            
                            # Add tool result to conversation
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result_text
                            })
                        else:
                            # Unknown tool
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: Unknown tool {function_name}"
                            })
                    
                    # Continue conversation (LLM will process tool results)
                    continue
                
                # No tool calls - LLM should be generating questions
                content = message.content.strip()
                
                if not content:
                    # Empty response, try again
                    messages.append({
                        "role": "user",
                        "content": "Please generate the questions in JSON format as requested."
                    })
                    continue
                
                # Try to extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        questions = parsed
                    elif isinstance(parsed, dict):
                        if "questions" in parsed:
                            questions = parsed["questions"]
                        else:
                            questions = [parsed]
                    else:
                        # Not valid JSON, ask LLM to retry
                        messages.append({
                            "role": "user",
                            "content": "Please output only a valid JSON array of questions. No other text."
                        })
                        continue
                    
                    # Successfully parsed questions
                    break
                    
                except json.JSONDecodeError:
                    # Invalid JSON, ask LLM to retry
                    messages.append({
                        "role": "user",
                        "content": "The response was not valid JSON. Please output only a valid JSON array of questions following the exact format specified."
                    })
                    continue
                    
            except Exception as e:
                # Handle rate limiting and retries
                error_msg = str(e).lower()
                if "429" in error_msg or "rate limit" in error_msg:
                    if iteration < max_retries:
                        wait_time = min(2 ** iteration, 60)
                        print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} retries")
                else:
                    raise e
        
        return questions if questions else []
    
    def _generate_questions_with_groq(
        self,
        prompt: str,
        max_retries: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using Groq API with rate limiting
        
        Args:
            prompt: Prompt string
            max_retries: Maximum retry attempts
            
        Returns:
            List of generated questions
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=4000
                )
                
                content = response.choices[0].message.content.strip()
                
                # Try to extract JSON from response
                # Remove markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                questions = json.loads(content)
                
                # Ensure it's a list
                if isinstance(questions, dict):
                    questions = [questions]
                
                return questions
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"JSON decode error, retrying... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)  # Wait before retry
                    continue
                raise ValueError(f"Failed to parse JSON response: {e}")
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a rate limit error
                if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                    wait_time = min(10 * (attempt + 1), 60)  # Exponential backoff, max 60s
                    print(f"Rate limit hit, waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    if attempt < max_retries - 1:
                        continue
                elif attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"API error, waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"Groq API error: {e}")
        
        return []
    
    def _check_duplicate(
        self,
        generated_question: Dict[str, Any],
        existing_questions: List[Dict[str, Any]],
        threshold: float = 0.95
    ) -> bool:
        """
        Check if generated question is too similar to existing questions
        
        Args:
            generated_question: Generated question
            existing_questions: List of existing questions
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if duplicate found
        """
        self._load_embedding_model()
        
        gen_text = generated_question.get("question", "")
        if not gen_text:
            return False
        
        if not existing_questions:
            return False
        
        # Batch encode all existing questions at once (more efficient)
        existing_texts = [
            q.get("question", "") for q in existing_questions 
            if q.get("question", "")
        ]
        
        if not existing_texts:
            return False
        
        # Generate embeddings in batch (single progress bar instead of many)
        gen_embedding = self.embedding_model.encode(gen_text, show_progress_bar=False)
        existing_embeddings = self.embedding_model.encode(existing_texts, show_progress_bar=False)
        
        # Calculate cosine similarities in batch
        gen_norm = np.linalg.norm(gen_embedding)
        similarities = np.dot(existing_embeddings, gen_embedding) / (
            np.linalg.norm(existing_embeddings, axis=1) * gen_norm
        )
        
        # Check if any similarity exceeds threshold
        if np.any(similarities > threshold):
            return True
        
        return False
    
    def _validate_question(self, question: Dict[str, Any]) -> bool:
        """
        Validate question format
        
        Args:
            question: Question dictionary
            
        Returns:
            True if valid
        """
        required_fields = ["question", "option1", "option2", "option3", "option4", "correct_option"]
        
        for field in required_fields:
            if field not in question:
                return False
        
        # Validate correct_option
        correct = question.get("correct_option")
        if not isinstance(correct, int) or correct < 1 or correct > 4:
            return False
        
        # Validate difficulty
        difficulty = question.get("difficulty", "").lower()
        if difficulty not in ["easy", "medium", "hard"]:
            return False
        
        return True
    
    def generate_questions(
        self,
        scrubbed_resume_text: str,
        scrubbed_jd_text: str,
        resume_skills: List[str],
        jd_skills: List[str],
        role: str,
        grade: str,
        domain: str,
        subtopics: List[str],
        count: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Generate questions based on requirements with full observability
        
        Args:
            scrubbed_resume_text: Full scrubbed resume text (no PII)
            scrubbed_jd_text: Full scrubbed job description text (no PII)
            resume_skills: Skills from resume (for RAG queries)
            jd_skills: Skills from JD (for RAG queries)
            role: Role name
            domain: Domain name
            subtopics: Relevant subtopics
            grade: Grade level (T2 or T3)
            count: Total number of questions to generate
            
        Returns:
            List of generated questions
        """
        # Calculate difficulty distribution
        dist = self._calculate_difficulty_distribution(grade, count)
        
        all_questions = []
        all_skills = list(set(resume_skills + jd_skills))  # Skills for RAG queries
        
        # Generate questions for each difficulty level
        for difficulty, num_questions in dist.items():
            if num_questions == 0:
                continue
            
            # Add delay between difficulty levels to avoid rate limiting
            if len(all_questions) > 0:
                print(f"Waiting 2 seconds before generating {difficulty} questions...")
                time.sleep(2)
            
            # Create agentic prompt (LLM will use RAG tool itself)
            system_prompt = self._create_agentic_prompt(
                role=role,
                domain=domain,
                difficulty=difficulty,
                grade=grade,
                subtopics=subtopics,
                skills=all_skills,
                resume_text=scrubbed_resume_text,
                jd_text=scrubbed_jd_text,
                count=num_questions
            )
            
            # Generate questions using agentic approach
            try:
                print(f"Generating {num_questions} {difficulty} questions using agentic approach (LLM will search RAG database)...")
                
                generated = self._generate_questions_agentic(
                    system_prompt=system_prompt,
                    difficulty=difficulty,
                    domain=domain
                )
                
                # Validate and filter
                for q in generated:
                    if self._validate_question(q):
                        # Ensure difficulty matches
                        q["difficulty"] = difficulty
                        # Add question_id
                        q["question_id"] = f"GEN_{len(all_questions) + 1:03d}"
                        all_questions.append(q)
                        
                        if len(all_questions) >= count:
                            break
                
                # If we need more questions, generate additional ones
                while len(all_questions) < count and len([q for q in all_questions if q.get("difficulty", "").lower() == difficulty]) < num_questions:
                    # Add delay before additional requests
                    time.sleep(2)
                    print(f"Generating 1 additional {difficulty} question...")
                    
                    # Create prompt for single question
                    single_prompt = self._create_agentic_prompt(
                        role=role,
                        domain=domain,
                        difficulty=difficulty,
                        grade=grade,
                        subtopics=subtopics,
                        skills=all_skills,
                        resume_text=scrubbed_resume_text,
                        jd_text=scrubbed_jd_text,
                        count=1
                    )
                    
                    # Generate additional question
                    additional = self._generate_questions_agentic(
                        system_prompt=single_prompt,
                        difficulty=difficulty,
                        domain=domain
                    )
                    
                    for q in additional:
                        if self._validate_question(q):
                            q["difficulty"] = difficulty
                            q["question_id"] = f"GEN_{len(all_questions) + 1:03d}"
                            all_questions.append(q)
                            
                            if len(all_questions) >= count:
                                break
                            
                            if len([q for q in all_questions if q.get("difficulty", "").lower() == difficulty]) >= num_questions:
                                break
                    
                    if len(all_questions) >= count:
                        break
                    
            except Exception as e:
                print(f"Error generating {difficulty} questions: {e}")
                continue
        
        return all_questions[:count]


# Global instance (will be initialized with API key)
question_generator = None

def get_question_generator(api_key: Optional[str] = None) -> QuestionGenerator:
    """Get or create question generator instance"""
    global question_generator
    if question_generator is None:
        question_generator = QuestionGenerator(api_key)
    return question_generator

