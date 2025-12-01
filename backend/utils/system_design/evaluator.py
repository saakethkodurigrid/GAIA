"""
Evaluation Engine using Groq LLM API
"""
import httpx
import re
from typing import Dict, Any, List, Optional
import json
from core.config import settings
from utils.system_design.models import Session
from utils.system_design.canvas_parser import CanvasParser
from utils.system_design.guardrails import guardrails


class EvaluationEngine:
    """Evaluates system designs using Groq LLM API"""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"  # Groq model (faster and more reliable)
        self.parser = CanvasParser()
        
        if not self.api_key:
            print("WARNING: GROQ_API_KEY not set! Evaluation will not work.")
            print("Please set GROQ_API_KEY in your environment or .env file")
    
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
        if not self.api_key:
            return {
                "scores": {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                },
                "feedback": "API key not configured. Please set GROQ_API_KEY to enable evaluation.",
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

EVALUATION CRITERIA (MANDATORY - Use these exact categories):
{evaluation_criteria}

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
  "feedback": "Provide comprehensive feedback addressing each category from the evaluation criteria. Reference specific components from the diagram. Be constructive and encouraging.",
  "follow_up": "Ask a thoughtful follow-up question related to the evaluation criteria that helps the candidate improve their design."
}}"""

        # Apply guardrails to prompts
        sanitized_system, sanitized_user, prompt_is_safe = guardrails.validate_and_sanitize_prompt(system_prompt, user_prompt)
        
        # Call Groq API
        try:
            response = await self._call_groq(sanitized_system, sanitized_user)
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
                "feedback": "⚠️ API error occurred during evaluation. Your design has been saved. Please check your GROQ_API_KEY configuration.",
                "follow_up": "Please check your API configuration to enable AI-powered evaluation."
            }
        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
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
            # Extract JSON from response
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            # Try to extract JSON if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            evaluation = json.loads(content)
            
            # Ensure all required fields
            if "scores" not in evaluation:
                evaluation["scores"] = {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                }
            
            return evaluation
            
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            print(f"Failed to parse JSON response: {e}")
            print(f"Response content: {response.get('choices', [{}])[0].get('message', {}).get('content', '')[:500]}")
            return {
                "scores": {
                    "architecture": 3.0,
                    "scalability": 3.0,
                    "reliability": 3.0,
                    "clarity": 3.0,
                    "consistency": 3.0
                },
                "feedback": response.get("choices", [{}])[0].get("message", {}).get("content", "Evaluation completed.")[:500],
                "follow_up": "Can you explain how your system handles high traffic?"
            }
    
    async def _call_groq(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Make API call to Groq"""
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 200  # Reduced to work within credit limits (concise responses)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            error_response_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
            print(f"Groq API HTTP error: {e.response.status_code}")
            print(f"Response body: {error_response_text}")
            print(f"Request URL: {self.api_url}")
            print(f"Request model: {self.model}")
            
            # Handle common Groq API errors
            if e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", "Bad request")
                    print(f"Groq API 400 Bad Request: {error_msg}")
                    raise ValueError(f"Bad request to Groq API: {error_msg}")
                except ValueError:
                    raise
                except:
                    raise ValueError(f"Bad request to Groq API: {error_response_text}")
            elif e.response.status_code == 401:
                raise ValueError("Invalid GROQ_API_KEY. Please check your API key.")
            elif e.response.status_code == 429:
                raise ValueError("Rate limit exceeded. Please try again later.")
            
            raise
        except Exception as e:
            print(f"Groq API error: {str(e)}")
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

