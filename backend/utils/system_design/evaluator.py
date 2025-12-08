"""
Evaluation Engine using LLM Provider Abstraction
"""
import httpx
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
import json
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage
from core.config import settings
from utils.system_design.models import Session
from utils.system_design.canvas_parser import CanvasParser
from utils.system_design.guardrails import guardrails

logger = logging.getLogger(__name__)


class EvaluationEngine:
    """Evaluates system designs using LLM API"""
    
    # Default fallback scores (consistent across all error cases)
    DEFAULT_FALLBACK_SCORES = {
        "core_functionality": 3.0,
        "architecture": 3.0,
        "scalability": 3.0,
        "reliability": 3.0,
        "design_quality": 3.0
    }
    
    # Maximum retry attempts for transient failures
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(self):
        self.parser = CanvasParser()
        
        # Use factory to get LLM provider with configured model
        try:
            self.llm = LLMProviderFactory.create_provider()
            self.model = self.llm.model  # Store the actual model being used
        except ValueError as e:
            logger.warning(f"LLM provider initialization failed: {str(e)}")
            logger.warning("Evaluation will not work. Please set LLM_PROVIDER and API key in your environment or .env file")
            self.llm = None
            self.model = None
    
    async def evaluate(
        self,
        canvas_json: Dict[str, Any],
        chat_text: str,
        question_text: str,
        evaluation_criteria: Optional[str] = None,
        evaluation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate figure + chat and return scores, feedback, and follow-up
        """
        if not self.llm:
            logger.warning("LLM not configured, returning fallback evaluation")
            return {
                "scores": self.DEFAULT_FALLBACK_SCORES.copy(),
                "feedback": "API key not configured. Please set LLM_PROVIDER and API key to enable evaluation.",
                "follow_up": "Please configure your API key to receive detailed feedback.",
                "metadata": {
                    "evaluation_quality": "fallback",
                    "error": "llm_not_configured",
                    "used_criteria": False
                }
            }
        
        # Parse canvas - this parses ALL elements
        parsed_data = self.parser.parse(canvas_json)
        graph_summary = self.parser.get_graph_summary(parsed_data)
        
        total_components = len(parsed_data["nodes"])
        total_connections = len(parsed_data["edges"])
        
        # Build detailed component list for LLM (include all if reasonable, otherwise sample)
        component_details = []
        nodes_to_include = parsed_data["nodes"] if total_components <= 50 else parsed_data["nodes"][:50]
        for node in nodes_to_include:
            node_id = node["id"]
            label = parsed_data["labels"].get(node_id, "Unlabeled")
            comp_type = parsed_data["component_types"].get(node_id, "unknown")
            details = f"- {label} ({comp_type})"
            if node_id in parsed_data["annotations"]:
                annots = parsed_data["annotations"][node_id]
                details += f" - Annotations: {annots}"
            component_details.append(details)
        
        if total_components > 50:
            component_details.append(f"\n... and {total_components - 50} more components")
        
        # Build connection details (include all if reasonable, otherwise sample)
        connection_details = []
        edges_to_include = parsed_data["edges"] if total_connections <= 50 else parsed_data["edges"][:50]
        for edge in edges_to_include:
            from_label = parsed_data["labels"].get(edge["from"], edge["from"][:8])
            to_label = parsed_data["labels"].get(edge["to"], edge["to"][:8])
            conn_str = f"{from_label} → {to_label}"
            if edge.get("label"):
                conn_str += f" (labeled: {edge['label']})"
            connection_details.append(conn_str)
        
        if total_connections > 50:
            connection_details.append(f"\n... and {total_connections - 50} more connections")
        
        # Sanitize chat text to prevent injection
        sanitized_chat_text, is_safe, warning = guardrails.sanitize_input(chat_text if chat_text else "")
        if not is_safe:
            print(f"[GUARDRAIL] Chat text flagged during evaluation: {warning}")
        
        # Always use database-driven evaluation criteria - it should always be provided
        if not evaluation_criteria:
            logger.warning("evaluation_criteria not provided. Evaluation may be less accurate.")
            # Generic fallback if somehow evaluation_criteria is missing
            system_prompt = """You are an experienced system design interviewer evaluating a candidate's design solution.
Your role is to provide a thorough, fair, and constructive evaluation based on industry best practices.

EVALUATION INSTRUCTIONS:
1. Analyze both the Excalidraw diagram (figure) and the candidate's explanation in the chat history
2. Evaluate the design based on general system design principles
3. Provide specific, actionable feedback that references actual components, connections, or design decisions from their diagram
4. Be constructive and encouraging - frame feedback as opportunities for improvement
5. Consider the overall design quality, completeness, and alignment with the problem requirements
6. Assess technical depth, scalability considerations, and architectural soundness
7. Note any missing critical components or design patterns that should be included
8. Acknowledge strengths while also identifying areas that need improvement

FEEDBACK STYLE:
- Be conversational and friendly, as if you're mentoring a colleague
- Use specific examples from their diagram
- Balance praise with constructive criticism
- Focus on the most impactful improvements first
- Keep feedback concise but comprehensive (3-5 sentences for feedback, 1-2 for follow-up)

SCORING GUIDELINES:
- Use a 1-5 scale for each evaluation dimension
- 1-2: Critical issues, fundamental gaps, or missing core components
- 3: Adequate but needs significant improvement
- 4: Good design with minor gaps or areas for enhancement
- 5: Excellent, production-ready design with comprehensive considerations

Provide your evaluation as JSON with scores, detailed feedback, and a thoughtful follow-up question."""
        else:
            # Use the evaluation criteria from the database with comprehensive system prompt
            # evaluation_criteria is the PRIMARY source (required)
            # evaluation_context is SUPPLEMENTAL (optional, provides domain-specific insights)
            
            # Build evaluation context section if available
            context_section = ""
            if evaluation_context:
                context_parts = []
                if evaluation_context.get("domain_specific_notes"):
                    context_parts.append(f"DOMAIN-SPECIFIC NOTES:\n{evaluation_context.get('domain_specific_notes')}")
                if evaluation_context.get("scoring_tips"):
                    context_parts.append(f"SCORING TIPS:\n{evaluation_context.get('scoring_tips')}")
                
                if context_parts:
                    context_section = f"""

ADDITIONAL EVALUATION CONTEXT (Use this to understand domain-specific nuances, but still evaluate based on the criteria above):
{chr(10).join(context_parts)}
"""
            
            system_prompt = f"""You are an experienced system design interviewer evaluating a candidate's design solution.
Your role is to provide a thorough, fair, and constructive evaluation STRICTLY based on the evaluation criteria provided below.

CRITICAL: You MUST evaluate using ONLY the categories and criteria specified below. Do NOT use generic categories.

EVALUATION CRITERIA (MANDATORY - Use these exact categories for evaluation, but DO NOT include them in your response):
{evaluation_criteria}{context_section}

CRITICAL OUTPUT RESTRICTIONS:
- DO NOT include the evaluation criteria text in your feedback or response
- DO NOT repeat or quote the evaluation criteria in your JSON response
- Only provide scores, feedback, and follow-up questions
- The feedback should be natural, conversational text - NOT a list of criteria
- Reference the criteria implicitly in your evaluation, but do not quote them
- Use the additional context to understand domain-specific nuances, but always evaluate based on the criteria above

EVALUATION INSTRUCTIONS:
1. Analyze both the Excalidraw diagram (figure) and the candidate's explanation in the chat history
2. Evaluate how well the candidate addressed EACH specific aspect mentioned in the evaluation criteria above
3. Extract the exact category names from the evaluation criteria (e.g., "Core Functionality", "System Architecture", "Scalability", etc.)
4. Score each category mentioned in the evaluation criteria on a 1-5 scale
5. If weightages are specified, consider them when providing overall feedback
6. Provide specific, actionable feedback that references actual components, connections, or design decisions from their diagram
7. Be constructive and encouraging - frame feedback as opportunities for improvement
8. Note any missing critical components or design patterns mentioned in the evaluation criteria
9. Acknowledge strengths while also identifying areas that need improvement based on the criteria
10. Use the additional context (if provided) to understand what strong candidates typically discuss for this domain

FEEDBACK STYLE:
- Be conversational and friendly, as if you're mentoring a colleague
- Use specific examples from their diagram (e.g., "I see you included a load balancer here, which is great for...")
- Balance praise with constructive criticism
- Focus on the most impactful improvements first based on the evaluation criteria
- Keep feedback concise but comprehensive (3-5 sentences for feedback, 1-2 for follow-up)

SCORING GUIDELINES:
- Use a 1-5 scale for each evaluation dimension specified in the criteria
- 1-2: Critical issues, fundamental gaps, or missing core components mentioned in criteria
- 3: Adequate but needs significant improvement in areas specified in criteria
- 4: Good design with minor gaps or areas for enhancement per criteria
- 5: Excellent, production-ready design with comprehensive considerations for all criteria points

IMPORTANT: Your JSON response must include scores for the EXACT categories mentioned in the evaluation criteria above. Do not use generic category names."""

        # Initialize expected_categories for validation
        expected_categories = []

        # Build dynamic JSON example based on evaluation_criteria if available
        if evaluation_criteria:
            # Extract category names from evaluation_criteria (look for numbered sections)
            # Try multiple patterns to find category headers
            categories = []
            
            # Improved category extraction with more patterns
            # Pattern 1: Numbered with bold "1. **Core Functionality**"
            pattern1 = r'\d+\.\s*\*\*([^*]+)\*\*'
            categories.extend(re.findall(pattern1, evaluation_criteria))
            
            # Pattern 2: Numbered without bold "1. Core Functionality"
            pattern2 = r'\d+\.\s*([A-Z][^:\n]+?)(?:\s*\(|:|\n|$)'
            categories.extend(re.findall(pattern2, evaluation_criteria))
            
            # Pattern 3: Bold text standalone "**Core Functionality**"
            pattern3 = r'\*\*([^*]+)\*\*'
            if not categories:
                categories.extend(re.findall(pattern3, evaluation_criteria))
            
            # Pattern 4: Headers with dashes "## Core Functionality"
            pattern4 = r'##+\s*([^\n]+)'
            categories.extend(re.findall(pattern4, evaluation_criteria))
            
            # Pattern 5: Uppercase headers "CORE FUNCTIONALITY:"
            pattern5 = r'^([A-Z][A-Z\s&]+?):'
            categories.extend(re.findall(pattern5, evaluation_criteria, re.MULTILINE))
            
            # Clean and deduplicate categories
            cleaned_categories = []
            seen = set()
            for cat in categories:
                cleaned = cat.strip()
                # Remove weightage info if present
                cleaned = re.sub(r'\s*\(Weight:.*?\)', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\s*Weight:.*?%', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'^#+\s*', '', cleaned)  # Remove markdown headers
                cleaned = cleaned.strip()
                # Filter out very short or generic categories
                if cleaned and len(cleaned) > 3 and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    cleaned_categories.append(cleaned)
            
            # Build scores object with found categories using consistent normalization
            if cleaned_categories:
                # Store original categories for validation
                expected_categories = cleaned_categories.copy()
                # Normalize category names consistently
                scores_example = {}
                for cat in cleaned_categories:
                    normalized = self._normalize_category_name(cat)
                    scores_example[normalized] = 3.5
                scores_example_str = ',\n    '.join([f'"{k}": {v}' for k, v in scores_example.items()])
            else:
                # Fallback if pattern doesn't match
                logger.warning("Could not extract categories from evaluation_criteria, using default")
                scores_example_str = '"core_functionality": 3.5,\n    "architecture": 3.0,\n    "scalability": 3.0,\n    "reliability": 3.0,\n    "design_quality": 3.0'
        else:
            scores_example_str = '"core_functionality": 3.5,\n    "architecture": 3.0,\n    "scalability": 3.0,\n    "reliability": 3.0,\n    "design_quality": 3.0'

        user_prompt = f"""QUESTION: {question_text}

FIGURE ANALYSIS (Complete Canvas Analysis):
{graph_summary}

TOTAL: {total_components} components, {total_connections} connections

COMPONENTS IN DIAGRAM ({len(component_details)} shown):
{chr(10).join(component_details) if component_details else "No components detected"}

CONNECTIONS IN DIAGRAM ({len(connection_details)} shown):
{chr(10).join(connection_details) if connection_details else "No connections detected"}

CANDIDATE EXPLANATION:
{sanitized_chat_text if sanitized_chat_text else "(No explanation provided yet)"}

CRITICAL INSTRUCTIONS:
1. Review the EVALUATION CRITERIA in the system prompt above
2. Extract the EXACT category names from the evaluation criteria (e.g., "Core Functionality", "System Architecture", "Scalability", "Reliability & Performance", "Design Quality")
3. Score EACH category mentioned in the evaluation criteria on a 1-5 scale
4. Use the EXACT category names (convert to lowercase with underscores for JSON keys, e.g., "Core Functionality" becomes "core_functionality")
5. Evaluate how well the candidate addressed each specific point mentioned under each category
6. If weightages are specified, consider them in your overall assessment

IMPORTANT: 
- Reference specific components from the diagram naturally in your feedback
- Be conversational and friendly - write like you're giving feedback to a colleague
- Focus on the most critical aspects relevant to this specific system design problem based on the evaluation criteria
- Keep feedback concise but helpful (3-5 sentences)
- Your scores object MUST include all categories from the evaluation criteria

The entire canvas has been analyzed ({total_components} components, {total_connections} connections).

Provide your response as JSON with the EXACT category names from the evaluation criteria:
{{
  "scores": {{
    {scores_example_str}
  }},
  "feedback": "Provide natural, conversational feedback (3-5 sentences) that references specific components from the diagram. Be constructive and encouraging. DO NOT list or quote the evaluation criteria - just provide your assessment naturally.",
  "follow_up": "Ask a thoughtful follow-up question that helps the candidate improve their design. Do not reference the evaluation criteria explicitly."
}}"""

        # Apply guardrails to prompts
        sanitized_system, sanitized_user, prompt_is_safe = guardrails.validate_and_sanitize_prompt(system_prompt, user_prompt)
        
        # Call LLM API with retry logic
        response = None
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._call_llm(sanitized_system, sanitized_user)
                break  # Success, exit retry loop
            except ValueError as e:
                # Configuration errors shouldn't be retried
                error_msg = str(e)
                logger.error(f"Configuration error (attempt {attempt + 1}): {error_msg}")
                return {
                    "scores": self.DEFAULT_FALLBACK_SCORES.copy(),
                    "feedback": "⚠️ API error occurred during evaluation. Your design has been saved. Please check your API configuration.",
                    "follow_up": "Please check your API configuration to enable AI-powered evaluation.",
                    "metadata": {
                        "evaluation_quality": "error",
                        "error": "configuration_error",
                        "error_message": error_msg,
                        "used_criteria": evaluation_criteria is not None
                    }
                }
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Check if it's a retryable error (rate limit, network issues)
                is_retryable = (
                    "429" in error_str or "rate limit" in error_str or 
                    "timeout" in error_str or "connection" in error_str or
                    "503" in error_str or "502" in error_str
                )
                
                if is_retryable and attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Retryable error (attempt {attempt + 1}/{self.MAX_RETRIES}): {str(e)}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Non-retryable error or max retries reached
                    logger.error(f"Error calling LLM API (attempt {attempt + 1}): {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "scores": self.DEFAULT_FALLBACK_SCORES.copy(),
                        "feedback": f"Error evaluating design: {str(e)}. Please check your API configuration or try again later.",
                        "follow_up": "Please try again or check your API configuration.",
                        "metadata": {
                            "evaluation_quality": "error",
                            "error": "llm_api_error",
                            "error_message": str(e),
                            "attempts": attempt + 1,
                            "used_criteria": evaluation_criteria is not None
                        }
                    }
        
        if not response:
            # All retries exhausted
            logger.error(f"All retry attempts failed. Last error: {last_error}")
            return {
                "scores": self.DEFAULT_FALLBACK_SCORES.copy(),
                "feedback": "Error evaluating design after multiple attempts. Please try again later.",
                "follow_up": "Please try again or check your API configuration.",
                "metadata": {
                    "evaluation_quality": "error",
                    "error": "max_retries_exceeded",
                    "error_message": str(last_error) if last_error else "Unknown error",
                    "attempts": self.MAX_RETRIES,
                    "used_criteria": evaluation_criteria is not None
                }
            }
        
        # Parse response with improved JSON extraction
        try:
            evaluation = self._parse_llm_response(response.content, expected_categories)
            
            # Validate and normalize scores
            evaluation = self._validate_and_normalize_evaluation(
                evaluation, 
                expected_categories,
                evaluation_criteria is not None
            )
            
            return evaluation
            
        except Exception as e:
            # Fallback if parsing completely fails
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response content preview: {response.content[:500] if response.content else 'None'}...")
            return {
                "scores": self.DEFAULT_FALLBACK_SCORES.copy(),
                "feedback": "Evaluation completed, but there was an issue parsing the detailed feedback. Your design has been saved.",
                "follow_up": "Can you explain how your system handles high traffic?",
                "metadata": {
                    "evaluation_quality": "error",
                    "error": "parse_error",
                    "error_message": str(e),
                    "used_criteria": evaluation_criteria is not None
                }
            }
    
    async def _call_llm(self, system_prompt: str, user_prompt: str):
        """Make API call to LLM using wrapper with lower temperature for consistent evaluation"""
        if not self.llm:
            raise ValueError("LLM provider not configured")
        
        try:
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ]
            # Lower temperature for more consistent, deterministic evaluation
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.2,  # Lowered from 0.7 for more consistent evaluation
                max_tokens=2000  # Increased to allow complete evaluation responses with scores, feedback, and follow-up
            )
            return response
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"LLM API error: {str(e)}")
            
            # Handle common LLM API errors
            if "400" in error_str or "bad request" in error_str:
                logger.error(f"LLM API 400 Bad Request: {str(e)}")
                raise ValueError(f"Bad request to LLM API: {str(e)}")
            elif "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                raise ValueError("Invalid API key. Please check your API key.")
            elif "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                raise ValueError("Rate limit exceeded. Please try again later.")
            
            raise
    
    def _normalize_category_name(self, category: str) -> str:
        """Normalize category name to consistent format for JSON keys"""
        normalized = category.lower().strip()
        # Replace common variations
        normalized = normalized.replace('&', 'and')
        normalized = normalized.replace('/', '_')
        normalized = normalized.replace('-', '_')
        normalized = normalized.replace(' ', '_')
        # Remove special characters
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        # Remove multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        return normalized
    
    def _parse_llm_response(self, content: str, expected_categories: List[str]) -> Dict[str, Any]:
        """Parse LLM response with improved JSON extraction"""
        if not content:
            raise ValueError("Empty response from LLM")
        
        # Step 1: Extract JSON from markdown code blocks
        if "```json" in content:
            parts = content.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0].strip()
                content = json_part
        elif "```" in content:
            # Try generic code block extraction
            parts = content.split("```")
            for i in range(1, len(parts), 2):
                potential_json = parts[i].strip()
                if potential_json.startswith("{") or potential_json.startswith("["):
                    content = potential_json
                    break
        
        # Step 2: Find JSON object boundaries
        if "{" not in content:
            raise ValueError("No JSON object found in response")
        
        # Remove text before first {
        content = content[content.index("{"):]
        
        # Step 3: Extract complete JSON by matching braces
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False
        
        for i, char in enumerate(content):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i
                        break
        
        if json_end >= 0:
            content = content[:json_end + 1]
        else:
            # Try to fix incomplete JSON
            while brace_count > 0:
                content += "}"
                brace_count -= 1
        
        # Step 4: Parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}. Attempting structured extraction...")
            # Fallback to structured extraction
            return self._extract_evaluation_fields(content)
    
    def _extract_evaluation_fields(self, content: str) -> Dict[str, Any]:
        """Extract evaluation fields using regex as fallback"""
        evaluation = {}
        
        # Extract scores object
        scores_match = re.search(r'"scores"\s*:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content, re.DOTALL)
        if scores_match:
            scores_text = "{" + scores_match.group(1) + "}"
            try:
                evaluation["scores"] = json.loads(scores_text)
            except json.JSONDecodeError:
                # Try to extract individual score pairs
                score_pairs = re.findall(r'"([^"]+)"\s*:\s*([0-9.]+)', scores_match.group(1))
                evaluation["scores"] = {k: float(v) for k, v in score_pairs}
        else:
            evaluation["scores"] = self.DEFAULT_FALLBACK_SCORES.copy()
        
        # Extract feedback (handle escaped quotes)
        feedback_match = re.search(r'"feedback"\s*:\s*"((?:[^"\\]|\\.)*)"', content, re.DOTALL)
        if feedback_match:
            evaluation["feedback"] = feedback_match.group(1).replace('\\"', '"').replace('\\n', '\n')
        else:
            evaluation["feedback"] = "Evaluation completed. Please continue working on your design."
        
        # Extract follow_up
        follow_up_match = re.search(r'"follow_up"\s*:\s*"((?:[^"\\]|\\.)*)"', content, re.DOTALL)
        if follow_up_match:
            evaluation["follow_up"] = follow_up_match.group(1).replace('\\"', '"').replace('\\n', '\n')
        else:
            evaluation["follow_up"] = "Can you explain how your system handles high traffic?"
        
        return evaluation
    
    def _validate_and_normalize_evaluation(
        self, 
        evaluation: Dict[str, Any], 
        expected_categories: List[str],
        used_criteria: bool
    ) -> Dict[str, Any]:
        """Validate scores, normalize categories, and add metadata"""
        # Ensure scores exist
        if "scores" not in evaluation or not isinstance(evaluation["scores"], dict):
            logger.warning("No scores found in evaluation, using defaults")
            evaluation["scores"] = self.DEFAULT_FALLBACK_SCORES.copy()
        
        # Validate and normalize scores
        validated_scores = {}
        for category, score in evaluation["scores"].items():
            # Normalize category name
            normalized_category = self._normalize_category_name(category)
            
            # Validate score is numeric and in range 1-5
            try:
                score_float = float(score)
                # Clamp to valid range
                if score_float < 1.0:
                    logger.warning(f"Score {score_float} for {category} is below 1.0, clamping to 1.0")
                    score_float = 1.0
                elif score_float > 5.0:
                    logger.warning(f"Score {score_float} for {category} is above 5.0, clamping to 5.0")
                    score_float = 5.0
                validated_scores[normalized_category] = round(score_float, 1)
            except (ValueError, TypeError):
                logger.warning(f"Invalid score '{score}' for category '{category}', using default 3.0")
                validated_scores[normalized_category] = 3.0
        
        evaluation["scores"] = validated_scores
        
        # Validate categories match expected (if criteria was provided)
        missing_categories = set()
        extra_categories = set()
        categories_match = None
        
        if used_criteria and expected_categories:
            expected_normalized = {self._normalize_category_name(cat) for cat in expected_categories}
            actual_normalized = set(validated_scores.keys())
            
            missing_categories = expected_normalized - actual_normalized
            extra_categories = actual_normalized - expected_normalized
            categories_match = len(missing_categories) == 0
            
            if missing_categories:
                logger.warning(f"Missing expected categories in evaluation: {missing_categories}")
            if extra_categories:
                logger.warning(f"Unexpected categories in evaluation: {extra_categories}")
        
        # Clean feedback field
        if "feedback" in evaluation and isinstance(evaluation["feedback"], str):
            feedback = evaluation["feedback"]
            # Remove JSON code blocks
            if "```json" in feedback:
                feedback = feedback.split("```json")[0].strip()
            elif "```" in feedback:
                feedback = feedback.split("```")[0].strip()
            # Remove raw JSON objects
            if feedback.startswith("{") and "}" in feedback:
                json_end = feedback.rindex("}")
                if json_end < len(feedback) - 1:
                    feedback = feedback[json_end + 1:].strip()
            evaluation["feedback"] = feedback
        
        # Add metadata
        evaluation["metadata"] = {
            "evaluation_quality": "success",
            "used_criteria": used_criteria,
            "expected_categories_count": len(expected_categories) if expected_categories else 0,
            "actual_categories_count": len(validated_scores),
            "categories_match": categories_match,
            "missing_categories": list(missing_categories) if missing_categories else [],
            "extra_categories": list(extra_categories) if extra_categories else []
        }
        
        return evaluation
    
    async def generate_final_report(self, session: Session, evaluation_criteria: Optional[str] = None, evaluation_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate final evaluation report for the session using LLM evaluation with evaluation_criteria from database"""
        
        # Get the latest canvas and chat history for comprehensive evaluation
        latest_canvas = session.current_canvas
        if not latest_canvas and session.canvas_versions:
            latest_canvas = session.canvas_versions[-1].data
        
        # Get all chat history
        chat_text = "\n".join([msg.content for msg in session.chat_history]) if session.chat_history else ""
        
        # Perform comprehensive final evaluation using LLM
        final_evaluation = None
        if latest_canvas:
            try:
                final_evaluation = await self.evaluate(
                    canvas_json=latest_canvas,
                    chat_text=chat_text,
                    question_text=session.question_text,
                    evaluation_criteria=evaluation_criteria,
                    evaluation_context=evaluation_context
                )
            except Exception as e:
                print(f"Error performing final LLM evaluation: {str(e)}")
                # Fall back to aggregating existing evaluations
        
        # Aggregate scores from all evaluations (including final one if available)
        all_scores = {}
        
        # Add existing evaluations
        for eval_obj in session.evaluations:
            for key, value in eval_obj.scores.items():
                if key not in all_scores:
                    all_scores[key] = []
                all_scores[key].append(value)
        
        # Add final evaluation if available
        if final_evaluation and "scores" in final_evaluation:
            for key, value in final_evaluation["scores"].items():
                if key not in all_scores:
                    all_scores[key] = []
                all_scores[key].append(value)
        
        # Calculate averages
        avg_scores = {
            key: sum(values) / len(values)
            for key, values in all_scores.items()
        } if all_scores else {}
        
        # Build timeline
        timeline = []
        for i, eval_obj in enumerate(session.evaluations):
            timeline.append({
                "version": eval_obj.version,
                "scores": eval_obj.scores,
                "feedback": eval_obj.feedback,
                "follow_up": eval_obj.follow_up
            })
        
        # Add final evaluation to timeline if available
        if final_evaluation:
            timeline.append({
                "version": "final",
                "scores": final_evaluation.get("scores", {}),
                "feedback": final_evaluation.get("feedback", "Final evaluation completed."),
                "follow_up": final_evaluation.get("follow_up", "Great work on your system design!")
            })
        
        # Generate summary
        lowest_score_key = min(avg_scores.items(), key=lambda x: x[1])[0] if avg_scores else None
        
        # Use final evaluation feedback as primary feedback if available
        primary_feedback = final_evaluation.get("feedback", "Evaluation completed.") if final_evaluation else "No evaluations available"
        
        return {
            "question_uuid": session.question_id,  # question_id is the question_uuid
            "question": session.question_text,
            "average_scores": avg_scores,
            "timeline": timeline,
            "total_versions": len(session.canvas_versions),
            "total_messages": len(session.chat_history),
            "lowest_area": lowest_score_key,
            "suggested_learning": self._get_learning_suggestions(avg_scores),
            "final_feedback": primary_feedback
        }
    
    def _get_learning_suggestions(self, scores: Dict[str, float]) -> List[str]:
        """Generate learning suggestions based on scores (dynamic, not hardcoded)"""
        suggestions = []
        
        # Find lowest scoring categories
        if not scores:
            return ["Continue practicing system design problems"]
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        lowest_categories = [cat for cat, score in sorted_scores if score < 3.0]
        
        # Generate suggestions based on actual low-scoring categories
        suggestion_map = {
            "scalability": "Study horizontal scaling patterns, load balancing strategies, and database partitioning techniques",
            "reliability": "Learn about redundancy, failover mechanisms, rate limiting, and distributed system resilience",
            "architecture": "Review RESTful API design, database schema design, and system organization patterns",
            "core_functionality": "Focus on understanding core system requirements and implementing fundamental functionality correctly",
            "design_quality": "Improve diagram clarity, consider edge cases, and practice explaining trade-offs",
            "performance": "Learn about caching strategies, database optimization, and performance monitoring",
            "security": "Study authentication, authorization, data encryption, and security best practices",
            "consistency": "Review CAP theorem, distributed consensus algorithms, and data consistency patterns"
        }
        
        for category in lowest_categories[:3]:  # Top 3 lowest
            normalized = self._normalize_category_name(category)
            # Try exact match first
            if normalized in suggestion_map:
                suggestions.append(suggestion_map[normalized])
            else:
                # Try partial match
                for key, suggestion in suggestion_map.items():
                    if key in normalized or normalized in key:
                        suggestions.append(suggestion)
                        break
        
        return suggestions if suggestions else ["Continue practicing system design problems"]

