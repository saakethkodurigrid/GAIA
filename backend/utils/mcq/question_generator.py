"""
Question Generator using LLM Provider Abstraction
Generates MCQ questions based on RAG examples and requirements
"""
import json
import time
import asyncio
import re
from typing import List, Dict, Optional, Any
from collections import defaultdict
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage
from core.config import settings
from services.mcq_rag_service import rag_system
from .rag_tool import get_rag_tool_definition, execute_rag_tool_call
from .domain_mapper import domain_mapper
import numpy as np
from sentence_transformers import SentenceTransformer


class QuestionGenerator:
    """Generates MCQ questions using LLM with RAG"""
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize question generator
        
        Args:
            groq_api_key: Groq API key (deprecated, kept for backward compatibility)
        """
        # Use factory to get LLM provider with configured model
        self.llm = LLMProviderFactory.create_provider()
        self.model = self.llm.model  # Store the actual model being used
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
        
        # Format subtopics as JSON array for tool call
        subtopics_json = json.dumps(subtopics) if subtopics else "[]"
        
        prompt = f"""You are an expert MCQ question generator for technical assessments.

Your task: Generate {count} NEW multiple-choice questions for a {difficulty} difficulty level ({grade} grade).

Role: {role}
Domain: {normalized_domain}
Difficulty: {difficulty} ({grade} level, requires {'deep understanding' if difficulty == 'hard' else 'moderate understanding' if difficulty == 'medium' else 'basic understanding'})

Candidate Background:
{resume_text}

Job Requirements:
{jd_text}

Relevant Subtopics to Cover:
{subtopics_text}

Key Skills: {skills_text}

You have access to a tool called `search_question_database` that lets you search for example questions from our dataset. 

WORKFLOW:
1. Use the `search_question_database` tool EXACTLY ONCE with the list of subtopics provided above to get all relevant examples at once.
   - Pass the subtopics as an array: {{"subtopics": {subtopics_json}, "difficulty": "{difficulty}", "domain": "{normalized_domain}"}}
   - This will search all subtopics and return combined, deduplicated results
   - CRITICAL: After making this ONE tool call, you MUST immediately generate questions. Do NOT make any more tool calls.
2. After receiving the tool results, analyze the example questions to understand the style, difficulty level, and topic coverage.
3. IMMEDIATELY generate {count} COMPLETELY NEW questions that:
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
- Call the search tool ONLY ONCE with all subtopics

Output Format (MUST be a JSON array of {count} question objects):
[
  {{
    "question": "Question text here?",
    "option1": "Option 1",
    "option2": "Option 2",
    "option3": "Option 3",
    "option4": "Option 4",
    "correct_option": 2,
    "difficulty": "{difficulty}",
    "tags": ["Tag1", "Tag2"]
  }},
  {{
    "question": "Another question text?",
    "option1": "Option A",
    "option2": "Option B",
    "option3": "Option C",
    "option4": "Option D",
    "correct_option": 3,
    "difficulty": "{difficulty}",
    "tags": ["Tag3"]
  }}
]

CRITICAL REQUIREMENTS:
- Output MUST be a JSON array (starts with [ and ends with ])
- The array must contain exactly {count} question objects
- Each question object must have: question, option1, option2, option3, option4, correct_option, difficulty, tags
- Do NOT wrap the array in markdown code blocks unless absolutely necessary
- Do NOT return a single object or an object with a "questions" key - return the array directly

IMPORTANT: Search the database ONCE with all subtopics, then IMMEDIATELY generate the questions. Do NOT make multiple tool calls. After the first tool call, you must generate questions, not make more tool calls."""
        
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
    
    async def _generate_questions_agentic(
        self,
        system_prompt: str,
        difficulty: str,
        domain: str,
        subtopics: List[str] = None,
        max_iterations: int = 10,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using agentic approach with function calling
        
        Args:
            system_prompt: System prompt for the LLM
            difficulty: Difficulty level
            domain: Domain name
            subtopics: List of subtopics to search (optional, for fallback)
            max_iterations: Maximum number of tool call iterations
            max_retries: Maximum retries for API calls
            
        Returns:
            List of generated questions
        """
        # Get RAG tool definition in standardized format
        rag_tool = get_rag_tool_definition()
        
        # Initialize conversation with standardized messages
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content="Please start by searching the database for relevant example questions using the subtopics provided, then generate the required questions.")
        ]
        
        # Tool executor function
        def tool_executor(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Execute tool calls"""
            print(f"  → Tool executor called: {tool_name}")
            print(f"  → Tool arguments: {json.dumps(arguments, indent=2)}")
            
            if tool_name == "search_question_database":
                # Normalize domain
                tool_domain = arguments.get("domain", domain)
                domain_mapping = {
                    "genai": "genAI",
                    "java_backend": "java_backend",
                    "python_backend": "python_backend",
                    "java": "java",
                    "cloud": "cloud"
                }
                normalized_domain = domain_mapping.get(tool_domain.lower(), tool_domain)
                
                # Check if subtopics are provided (preferred approach)
                tool_subtopics = arguments.get("subtopics")
                query_text = arguments.get("query_text")
                
                # If no subtopics in arguments but we have them in context, use them
                if not tool_subtopics and subtopics:
                    tool_subtopics = subtopics
                    print(f"  → Using subtopics from context: {len(tool_subtopics)} subtopics")
                
                print(f"  → Executing RAG search: domain={normalized_domain}, difficulty={difficulty}, subtopics={len(tool_subtopics) if tool_subtopics else 0}")
                
                result = execute_rag_tool_call(
                    query_text=query_text if not tool_subtopics else None,
                    subtopics=tool_subtopics,
                    difficulty=arguments.get("difficulty", difficulty),
                    domain=normalized_domain,
                    top_k=arguments.get("top_k", 10)
                )
                
                print(f"  → RAG search returned {result['count']} questions")
                
                # Format result for LLM
                search_count = len(tool_subtopics) if tool_subtopics and len(tool_subtopics) > 0 else 1
                tool_result_text = f"""Tool call result:
Found {result['count']} similar questions across {search_count} search{'es' if search_count > 1 else ''}.

Example questions (for inspiration only, DO NOT duplicate):
"""
                for i, q in enumerate(result['questions'][:15], 1):  # Show top 15 examples
                    tool_result_text += f"""
{i}. {q['question']}
   Options: {q['options'][0]}, {q['options'][1]}, {q['options'][2]}, {q['options'][3]}
   Correct: Option {q['correct_option']}
   Tags: {', '.join(q.get('tags', []))}
"""
                
                print(f"  → Tool result length: {len(tool_result_text)} chars")
                return {"content": tool_result_text}
            else:
                error_msg = f"Unknown tool: {tool_name}"
                print(f"  → ERROR: {error_msg}")
                return {"error": error_msg}
        
        questions = []
        tool_call_count = 0
        max_tool_calls = 2  # Limit tool calls to prevent infinite loops
        
        for iteration in range(max_iterations):
            try:
                print(f"\n  → Iteration {iteration + 1}/{max_iterations}: Calling LLM...")
                
                # Print input messages for debugging
                print(f"  → Input messages ({len(messages)} total, showing last 3):")
                for i, msg in enumerate(messages[-3:], 1):  # Show last 3 messages
                    role = msg.role
                    content_preview = str(msg.content)[:400] if msg.content else "(empty)"
                    if len(str(msg.content)) > 400:
                        content_preview += "..."
                    print(f"    [{i}] {role}: {content_preview}")
                
                # Use LLM wrapper with tool execution
                response = await self.llm.chat_completion_with_tools(
                    messages=messages,
                    tools=[rag_tool],
                    tool_executor=tool_executor,
                    max_iterations=1,  # We handle iteration manually
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=4000
                )
                
                # Print response details
                print(f"  → LLM Response:")
                print(f"    - Content length: {len(response.content) if response.content else 0}")
                print(f"    - Tool calls: {len(response.tool_calls) if response.tool_calls else 0}")
                
                if response.content:
                    content_preview = response.content[:1000] if len(response.content) > 1000 else response.content
                    print(f"    - Content preview: {content_preview}")
                    if len(response.content) > 1000:
                        print(f"    - ... (truncated, total {len(response.content)} chars)")
                    # Also print full content if it's not too long
                    if len(response.content) <= 2000:
                        print(f"    - Full content: {response.content}")
                
                if response.tool_calls:
                    for i, tool_call in enumerate(response.tool_calls, 1):
                        print(f"    - Tool call {i}: {tool_call.name}")
                        args_str = json.dumps(tool_call.arguments, indent=2)
                        if len(args_str) > 500:
                            args_str = args_str[:500] + "..."
                        print(f"      Arguments: {args_str}")
                
                # Check if we got tool calls (this means we need to continue)
                if response.tool_calls:
                    tool_call_count += len(response.tool_calls)
                    print(f"  → Iteration {iteration + 1}: LLM made {len(response.tool_calls)} tool call(s) (total: {tool_call_count})")
                    
                    # CRITICAL FIX: chat_completion_with_tools executes tools internally but doesn't update our messages list
                    # We need to manually add the assistant response and tool results to our messages
                    # so the LLM sees them in the next iteration
                    
                    # Add assistant response with tool calls
                    assistant_content = response.content or ""
                    print(f"  → Adding assistant response with {len(response.tool_calls)} tool call(s) to messages")
                    
                    # For Anthropic, format assistant message with tool_use blocks
                    assistant_content_blocks = []
                    if assistant_content:
                        assistant_content_blocks.append({"type": "text", "text": assistant_content})
                    for tool_call in response.tool_calls:
                        assistant_content_blocks.append({
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.arguments
                        })
                    
                    messages.append(LLMMessage(
                        role="assistant",
                        content=json.dumps(assistant_content_blocks)
                    ))
                    
                    # Add tool results (chat_completion_with_tools already executed them, but we need to add to our messages)
                    # Re-execute to get results (inefficient but necessary since we don't have access to internal state)
                    tool_result_blocks = []
                    for tool_call in response.tool_calls:
                        print(f"  → Re-executing tool {tool_call.name} to get result for messages...")
                        tool_result = tool_executor(tool_call.name, tool_call.arguments)
                        
                        # Extract content from tool_result
                        # The tool_executor returns {"content": "..."}, so extract the content string
                        if isinstance(tool_result, dict):
                            # If tool_result has a "content" key, use that directly (it's already a string)
                            if "content" in tool_result:
                                tool_result_content = str(tool_result["content"])
                            else:
                                # No "content" key, stringify the whole dict
                                tool_result_content = json.dumps(tool_result, indent=2)
                        else:
                            # Not a dict, convert to string
                            tool_result_content = str(tool_result)
                        
                        # Create tool_result block according to Anthropic format
                        tool_result_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": tool_result_content
                        })
                    
                    # Add tool results as user message (Anthropic format)
                    # CRITICAL: Store as JSON string, but _convert_messages_to_anthropic_format will parse it
                    # The content should be a list of content blocks, not a JSON string
                    if tool_result_blocks:
                        # Store as JSON string - the conversion function will parse it for user messages with tool results
                        messages.append(LLMMessage(
                            role="user",
                            content=json.dumps(tool_result_blocks)
                        ))
                        print(f"  → Added {len(tool_result_blocks)} tool result(s) to messages")
                    
                    # If we've made too many tool calls, force question generation
                    if tool_call_count >= max_tool_calls:
                        print(f"  → Reached max tool calls ({max_tool_calls}), forcing question generation...")
                        force_message = "You have already searched the database. Now please generate the questions in JSON format as requested. Do not make any more tool calls."
                        print(f"  → Adding force message: {force_message}")
                        messages.append(LLMMessage(
                            role="user",
                            content=force_message
                        ))
                        continue
                    
                    # Tool calls were executed and added to messages, continue loop
                    print(f"  → Updated messages list, now has {len(messages)} messages")
                    continue
                
                # No tool calls - LLM should be generating questions
                content = response.content.strip()
                
                print(f"  → Iteration {iteration + 1}: No tool calls, content length: {len(content) if content else 0}")
                if content:
                    if len(content) <= 2000:
                        print(f"  → Full content: {content}")
                    else:
                        print(f"  → Full content (first 2000 chars): {content[:2000]}...")
                        print(f"  → ... (remaining {len(content) - 2000} chars)")
                
                if not content:
                    # Empty response, try again
                    print(f"  → Iteration {iteration + 1}: Empty response, asking LLM to generate questions...")
                    messages.append(LLMMessage(
                        role="user",
                        content="Please generate the questions in JSON format as requested."
                    ))
                    continue
                
                # Try to extract JSON from response
                original_content = content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON array in content (in case LLM adds extra text)
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    content = json_match.group(0)
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    
                    # Validate it's the expected format
                    if isinstance(parsed, list):
                        # Perfect - it's an array
                        questions = parsed
                        print(f"  → Parsed JSON array with {len(questions)} questions")
                    elif isinstance(parsed, dict):
                        # Fallback: check if it has a "questions" key
                        if "questions" in parsed and isinstance(parsed["questions"], list):
                            questions = parsed["questions"]
                            print(f"  → Parsed dict with 'questions' key, found {len(questions)} questions")
                        else:
                            # Single object - wrap it
                            questions = [parsed]
                            print(f"  → Parsed single object, wrapped in array")
                    else:
                        # Not valid format
                        print(f"  → Parsed JSON but got unexpected type: {type(parsed)}")
                        messages.append(LLMMessage(
                            role="user",
                            content="Please output a JSON array of questions (starts with [ and ends with ]). The response must be an array, not a single object or other format."
                        ))
                        continue
                    
                    # Successfully parsed questions
                    if questions:
                        print(f"  → Successfully parsed {len(questions)} questions from LLM response")
                    else:
                        print(f"  → Warning: Parsed JSON but got empty questions list")
                    break
                    
                except json.JSONDecodeError as json_err:
                    # Invalid JSON, ask LLM to retry
                    print(f"  → JSON decode error on iteration {iteration + 1}: {json_err}")
                    if iteration < max_iterations - 1:
                        messages.append(LLMMessage(
                            role="user",
                            content="The response was not valid JSON. Please output only a valid JSON array of questions following the exact format specified."
                        ))
                        continue
                    else:
                        print(f"  → Max iterations reached, returning empty list")
                        break
                    
            except Exception as e:
                # Handle rate limiting and retries
                error_msg = str(e).lower()
                if "429" in error_msg or "rate limit" in error_msg:
                    if iteration < max_retries:
                        wait_time = min(2 ** iteration, 60)
                        print(f"  → Rate limited. Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} retries")
                else:
                    print(f"  → Error on iteration {iteration + 1}: {e}")
                    raise e
        
        if not questions:
            print(f"  → Warning: _generate_questions_agentic returning empty list after {max_iterations} iterations")
        
        return questions if questions else []
    
    async def _generate_questions_with_llm(
        self,
        prompt: str,
        max_retries: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using LLM API with rate limiting
        
        Args:
            prompt: Prompt string
            max_retries: Maximum retry attempts
            
        Returns:
            List of generated questions
        """
        for attempt in range(max_retries):
            try:
                messages = [LLMMessage(role="user", content=prompt)]
                response = await self.llm.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=4000
                )
                
                content = response.content.strip()
                
                # Try to extract JSON from response
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
                    time.sleep(2)
                    continue
                raise ValueError(f"Failed to parse JSON response: {e}")
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                    wait_time = min(10 * (attempt + 1), 60)
                    print(f"Rate limit hit, waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    if attempt < max_retries - 1:
                        continue
                elif attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"API error, waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"LLM API error: {e}")
        
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
    
    async def generate_questions(
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
        # Step 1: Calculate difficulty distribution
        dist = self._calculate_difficulty_distribution(grade, count)
        
        # Step 2: Initialize tracking
        all_questions = []
        all_skills = list(set(resume_skills + jd_skills))
        difficulty_counts = defaultdict(int)  # Track counts per difficulty
        seen_questions = set()  # For deduplication
        
        # Step 3: Pre-create prompts (cache them)
        prompts_cache = {}
        for difficulty, num_questions in dist.items():
            if num_questions > 0:
                prompts_cache[difficulty] = self._create_agentic_prompt(
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
        
        # Step 4: Generate questions for each difficulty level
        for difficulty, num_questions in dist.items():
            if num_questions == 0:
                continue
            
            if len(all_questions) >= count:
                break
            
            remaining_for_difficulty = num_questions - difficulty_counts[difficulty]
            if remaining_for_difficulty <= 0:
                continue
            
            try:
                print(f"Generating {remaining_for_difficulty} {difficulty} questions using agentic approach...")
                
                # Use cached prompt
                system_prompt = prompts_cache[difficulty]
                
                generated = await self._generate_questions_agentic(
                    system_prompt=system_prompt,
                    difficulty=difficulty,
                    domain=domain,
                    subtopics=subtopics
                )
                
                # Log what we got from LLM
                print(f"  → Received {len(generated)} questions from LLM for {difficulty}")
                
                # Validate, deduplicate, and add questions
                validated_count = 0
                duplicate_count = 0
                invalid_count = 0
                
                for q in generated:
                    if len(all_questions) >= count:
                        break
                    
                    if difficulty_counts[difficulty] >= num_questions:
                        break
                    
                    # Deduplication check
                    question_text = q.get("question", "").strip().lower()
                    if not question_text:
                        invalid_count += 1
                        continue
                    
                    if question_text in seen_questions:
                        duplicate_count += 1
                        continue
                    
                    if self._validate_question(q):
                        q["difficulty"] = difficulty
                        q["question_id"] = f"GEN_{len(all_questions) + 1:03d}"
                        all_questions.append(q)
                        seen_questions.add(question_text)
                        difficulty_counts[difficulty] += 1
                        validated_count += 1
                    else:
                        invalid_count += 1
                
                # Log filtering results
                print(f"  → Added {validated_count} valid questions, {duplicate_count} duplicates, {invalid_count} invalid")
                print(f"  → Current {difficulty} count: {difficulty_counts[difficulty]}/{num_questions}")
                
                # Retry logic with better approach
                max_retries = 3
                retry_count = 0
                
                while (len(all_questions) < count and 
                       difficulty_counts[difficulty] < num_questions and 
                       retry_count < max_retries):
                    
                    remaining = min(
                        num_questions - difficulty_counts[difficulty],
                        count - len(all_questions)
                    )
                    
                    if remaining <= 0:
                        break
                    
                    # Use async sleep instead of blocking sleep
                    await asyncio.sleep(1)  # Reduced from 2 seconds
                    retry_count += 1
                    
                    print(f"Generating {remaining} additional {difficulty} question(s) (retry {retry_count}/{max_retries})...")
                    
                    # Create prompt for remaining questions (not just 1)
                    retry_prompt = self._create_agentic_prompt(
                        role=role,
                        domain=domain,
                        difficulty=difficulty,
                        grade=grade,
                        subtopics=subtopics,
                        skills=all_skills,
                        resume_text=scrubbed_resume_text,
                        jd_text=scrubbed_jd_text,
                        count=remaining  # Generate remaining amount, not just 1
                    )
                    
                    try:
                        additional = await self._generate_questions_agentic(
                            system_prompt=retry_prompt,
                            difficulty=difficulty,
                            domain=domain,
                            subtopics=subtopics
                        )
                        
                        print(f"  → Retry {retry_count}: Received {len(additional)} questions from LLM")
                        
                        retry_validated = 0
                        retry_duplicate = 0
                        retry_invalid = 0
                        
                        for q in additional:
                            if len(all_questions) >= count:
                                break
                            
                            if difficulty_counts[difficulty] >= num_questions:
                                break
                            
                            # Deduplication
                            question_text = q.get("question", "").strip().lower()
                            if not question_text:
                                retry_invalid += 1
                                continue
                            
                            if question_text in seen_questions:
                                retry_duplicate += 1
                                continue
                            
                            if self._validate_question(q):
                                q["difficulty"] = difficulty
                                q["question_id"] = f"GEN_{len(all_questions) + 1:03d}"
                                all_questions.append(q)
                                seen_questions.add(question_text)
                                difficulty_counts[difficulty] += 1
                                retry_validated += 1
                            else:
                                retry_invalid += 1
                        
                        print(f"  → Retry {retry_count}: Added {retry_validated} valid, {retry_duplicate} duplicates, {retry_invalid} invalid")
                        print(f"  → Current {difficulty} count: {difficulty_counts[difficulty]}/{num_questions}")
                        
                        # If we got enough questions, exit retry loop
                        if difficulty_counts[difficulty] >= num_questions:
                            break
                            
                    except Exception as retry_error:
                        print(f"Error in retry {retry_count} for {difficulty} questions: {retry_error}")
                        # Continue to next retry
                        continue
                    
            except Exception as e:
                print(f"Error generating {difficulty} questions: {e}")
                import traceback
                traceback.print_exc()  # Better error logging
                continue
        
        # Step 5: Final validation and return
        final_questions = all_questions[:count]
        
        # Log summary
        print(f"\n=== Question Generation Summary ===")
        print(f"Total requested: {count}")
        print(f"Total generated: {len(final_questions)}")
        for diff in ["hard", "medium", "easy"]:
            actual = len([q for q in final_questions if q.get("difficulty") == diff])
            expected = dist.get(diff, 0)
            print(f"{diff.capitalize()}: {actual}/{expected}")
        print("=" * 40)
        
        return final_questions


# Global instance (will be initialized with API key)
question_generator = None

def get_question_generator(api_key: Optional[str] = None) -> QuestionGenerator:
    """Get or create question generator instance"""
    global question_generator
    if question_generator is None:
        question_generator = QuestionGenerator(api_key)
    return question_generator

