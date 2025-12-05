"""
Evaluation Engine using LLM Provider Abstraction
"""
import httpx
import re
from typing import Dict, Any, List, Optional
import json
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage
from core.config import settings
from utils.system_design.models import Session
from utils.system_design.canvas_parser import CanvasParser
from utils.system_design.guardrails import guardrails


class EvaluationEngine:
    """Evaluates system designs using LLM API"""
    
    def __init__(self):
        self.parser = CanvasParser()
        
        # Use factory to get LLM provider with configured model
        try:
            self.llm = LLMProviderFactory.create_provider()
            self.model = self.llm.model  # Store the actual model being used
        except ValueError as e:
            print(f"WARNING: {str(e)}")
            print("Evaluation will not work. Please set LLM_PROVIDER and API key in your environment or .env file")
            self.llm = None
            self.model = None
    
    async def evaluate(
        self,
        canvas_json: Dict[str, Any],
        chat_text: str,
        question_text: str,
        evaluation_criteria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate figure + chat and return scores, feedback, and follow-up
        """
        if not self.llm:
            return {
                "scores": {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                },
                "feedback": "API key not configured. Please set LLM_PROVIDER and API key to enable evaluation.",
                "follow_up": "Please configure your API key to receive detailed feedback."
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
            print("WARNING: evaluation_criteria not provided. Evaluation may be less accurate.")
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
            system_prompt = f"""You are an experienced system design interviewer evaluating a candidate's design solution.
Your role is to provide a thorough, fair, and constructive evaluation STRICTLY based on the evaluation criteria provided below.

CRITICAL: You MUST evaluate using ONLY the categories and criteria specified below. Do NOT use generic categories.

EVALUATION CRITERIA (MANDATORY - Use these exact categories for evaluation, but DO NOT include them in your response):
{evaluation_criteria}

CRITICAL OUTPUT RESTRICTIONS:
- DO NOT include the evaluation criteria text in your feedback or response
- DO NOT repeat or quote the evaluation criteria in your JSON response
- Only provide scores, feedback, and follow-up questions
- The feedback should be natural, conversational text - NOT a list of criteria
- Reference the criteria implicitly in your evaluation, but do not quote them

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

        # Build dynamic JSON example based on evaluation_criteria if available
        if evaluation_criteria:
            # Extract category names from evaluation_criteria (look for numbered sections)
            # Try multiple patterns to find category headers
            # Pattern 1: "1. **Core Functionality**" or "1. Core Functionality"
            # Pattern 2: "**Core Functionality**" (without number)
            # Pattern 3: "Core Functionality (Weight: 25%)"
            categories = []
            
            # Pattern 1: Numbered with bold
            pattern1 = r'\d+\.\s*\*\*([^*]+)\*\*'
            categories.extend(re.findall(pattern1, evaluation_criteria))
            
            # Pattern 2: Numbered without bold
            pattern2 = r'\d+\.\s*([A-Z][^:]+?)(?:\s*\(|:)'
            categories.extend(re.findall(pattern2, evaluation_criteria))
            
            # Pattern 3: Bold text (fallback)
            if not categories:
                pattern3 = r'\*\*([^*]+)\*\*'
                categories.extend(re.findall(pattern3, evaluation_criteria))
            
            # Clean and deduplicate categories
            cleaned_categories = []
            seen = set()
            for cat in categories:
                cleaned = cat.strip()
                # Remove weightage info if present
                cleaned = re.sub(r'\s*\(Weight:.*?\)', '', cleaned)
                cleaned = re.sub(r'\s*Weight:.*?%', '', cleaned)
                cleaned = cleaned.strip()
                if cleaned and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    cleaned_categories.append(cleaned)
            
            # Build scores object with found categories
            if cleaned_categories:
                scores_example = {cat.lower().replace(' ', '_').replace('&', 'and').replace('/', '_'): 3.5 for cat in cleaned_categories}
                scores_example_str = ',\n    '.join([f'"{k}": {v}' for k, v in scores_example.items()])
            else:
                # Fallback if pattern doesn't match
                scores_example_str = '"core_functionality": 3.5,\n    "architecture": 3.0,\n    "scalability": 2.5,\n    "reliability": 3.0,\n    "design_quality": 4.0'
        else:
            scores_example_str = '"core_functionality": 3.5,\n    "architecture": 3.0,\n    "scalability": 2.5,\n    "reliability": 3.0,\n    "design_quality": 4.0'

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
        
        # Call LLM API
        try:
            response = await self._call_llm(sanitized_system, sanitized_user)
        except ValueError as e:
            # Handle credit/configuration errors specifically
            error_msg = str(e)
            print(f"Configuration error: {error_msg}")
            return {
                "scores": {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                },
                "feedback": "⚠️ API error occurred during evaluation. Your design has been saved. Please check your API configuration.",
                "follow_up": "Please check your API configuration to enable AI-powered evaluation."
            }
        except Exception as e:
            print(f"Error calling LLM API: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "scores": {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                },
                "feedback": f"Error evaluating design: {str(e)}. Please check your API configuration or try again later.",
                "follow_up": "Please try again or check your API configuration."
            }
        
        # Parse response
        try:
            # Extract JSON from response (LLM wrapper returns standardized response)
            content = response.content or "{}"
            
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in content:
                # Extract content between ```json and ```
                parts = content.split("```json")
                if len(parts) > 1:
                    json_part = parts[1].split("```")[0].strip()
                    content = json_part
            elif "```" in content:
                # Try generic code block extraction
                parts = content.split("```")
                if len(parts) > 1:
                    # Take the first code block that looks like JSON
                    for i in range(1, len(parts), 2):
                        potential_json = parts[i].strip()
                        if potential_json.startswith("{") or potential_json.startswith("["):
                            content = potential_json
                            break
            
            # Clean up any remaining markdown or extra text
            # Remove any text before the first {
            if "{" in content:
                content = content[content.index("{"):]
            
            # Try to extract complete JSON by matching braces
            # This handles truncated responses better
            brace_count = 0
            json_end = -1
            for i, char in enumerate(content):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i
                        break
            
            if json_end >= 0:
                # Found complete JSON object
                content = content[:json_end + 1]
            else:
                # JSON might be truncated, try to fix it
                # Add closing braces if needed
                while brace_count > 0:
                    content += "}"
                    brace_count -= 1
                # Ensure proper closing
                if not content.rstrip().endswith("}"):
                    # Try to extract what we can
                    # Find the last complete field
                    if '"feedback"' in content:
                        # Try to extract up to feedback field
                        feedback_start = content.find('"feedback"')
                        if feedback_start > 0:
                            # Find the value after feedback
                            value_start = content.find(':', feedback_start)
                            if value_start > 0:
                                # Try to find the end of the feedback string
                                quote_start = content.find('"', value_start)
                                if quote_start > 0:
                                    quote_end = content.find('"', quote_start + 1)
                                    if quote_end > 0:
                                        # We have at least the feedback field, close the JSON
                                        content = content[:quote_end + 1] + '}'
            
            try:
                evaluation = json.loads(content)
            except json.JSONDecodeError as parse_error:
                # If still failing, try to extract fields manually
                print(f"JSON parse error after cleanup: {parse_error}")
                print(f"Content length: {len(content)}, Content preview: {content[:200]}...")
                
                # Try to extract scores and feedback using regex as fallback
                scores_match = re.search(r'"scores"\s*:\s*\{([^}]+)\}', content)
                feedback_match = re.search(r'"feedback"\s*:\s*"([^"]+)"', content)
                follow_up_match = re.search(r'"follow_up"\s*:\s*"([^"]+)"', content)
                
                evaluation = {}
                if scores_match:
                    # Try to parse scores
                    scores_text = "{" + scores_match.group(1) + "}"
                    try:
                        evaluation["scores"] = json.loads(scores_text)
                    except:
                        evaluation["scores"] = {
                            "core_functionality": 1.0,
                            "system_architecture": 1.0,
                            "scalability": 1.0,
                            "reliability_and_performance": 1.0,
                            "design_quality": 1.0
                        }
                else:
                    evaluation["scores"] = {
                        "core_functionality": 1.0,
                        "system_architecture": 1.0,
                        "scalability": 1.0,
                        "reliability_and_performance": 1.0,
                        "design_quality": 1.0
                    }
                
                evaluation["feedback"] = feedback_match.group(1) if feedback_match else "Evaluation completed. Please continue working on your design."
                evaluation["follow_up"] = follow_up_match.group(1) if follow_up_match else "Can you explain how your system handles high traffic?"
            
            # Ensure all required fields and clean up feedback
            if "scores" not in evaluation:
                evaluation["scores"] = {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                }
            
            # Clean feedback field - remove any JSON code blocks or raw JSON
            if "feedback" in evaluation and isinstance(evaluation["feedback"], str):
                feedback = evaluation["feedback"]
                # Remove any JSON code blocks from feedback
                if "```json" in feedback:
                    feedback = feedback.split("```json")[0].strip()
                elif "```" in feedback:
                    feedback = feedback.split("```")[0].strip()
                # Remove any raw JSON objects from feedback
                if feedback.startswith("{") and "}" in feedback:
                    # Try to extract text after JSON
                    json_end = feedback.rindex("}")
                    if json_end < len(feedback) - 1:
                        feedback = feedback[json_end + 1:].strip()
                evaluation["feedback"] = feedback
            
            return evaluation
            
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            print(f"Failed to parse JSON response: {e}")
            content = response.content or "Evaluation completed."
            print(f"Response content: {content[:500]}")
            return {
                "scores": {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                },
                "feedback": content[:500],
                "follow_up": "Can you explain how your system handles high traffic?"
            }
    
    async def _call_llm(self, system_prompt: str, user_prompt: str):
        """Make API call to LLM using wrapper"""
        if not self.llm:
            raise ValueError("LLM provider not configured")
        
        try:
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ]
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=2000  # Increased to allow complete evaluation responses with scores, feedback, and follow-up
            )
            return response
        except Exception as e:
            error_str = str(e).lower()
            print(f"LLM API error: {str(e)}")
            
            # Handle common LLM API errors
            if "400" in error_str or "bad request" in error_str:
                print(f"LLM API 400 Bad Request: {str(e)}")
                raise ValueError(f"Bad request to LLM API: {str(e)}")
            elif "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                raise ValueError("Invalid API key. Please check your API key.")
            elif "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                raise ValueError("Rate limit exceeded. Please try again later.")
            
            raise
    
    async def generate_final_report(self, session: Session, evaluation_criteria: Optional[str] = None) -> Dict[str, Any]:
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
                    evaluation_criteria=evaluation_criteria
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
            "session_id": session.session_id,
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
        """Generate learning suggestions based on scores"""
        suggestions = []
        
        if scores.get("scalability", 5) < 3:
            suggestions.append("Study horizontal scaling patterns, load balancing strategies, and database partitioning techniques")
        
        if scores.get("reliability", 5) < 3:
            suggestions.append("Learn about redundancy, failover mechanisms, rate limiting, and distributed system resilience")
        
        if scores.get("architecture", 5) < 3:
            suggestions.append("Review RESTful API design, database schema design, and system organization patterns")
        
        if scores.get("core_functionality", 5) < 3:
            suggestions.append("Focus on understanding core system requirements and implementing fundamental functionality correctly")
        
        if scores.get("design_quality", 5) < 3:
            suggestions.append("Improve diagram clarity, consider edge cases, and practice explaining trade-offs")
        
        return suggestions if suggestions else ["Continue practicing system design problems"]

