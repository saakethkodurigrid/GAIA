"""
Evaluation Engine using Groq LLM API
"""
import httpx
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
        
        # Use database-driven evaluation criteria if provided, otherwise use default
        if evaluation_criteria:
            # Use the evaluation criteria from the database
            system_prompt = f"""You are an experienced system design interviewer evaluating a candidate's design.
Analyze both the figure (Excalidraw diagram) and the candidate's explanation.

{evaluation_criteria}

Provide constructive, conversational feedback. Be friendly and encouraging, like you're helping them improve.
Reference specific components from their diagram naturally."""
        else:
            # Fallback to default URL Shortener criteria
            system_prompt = """You are an experienced system design interviewer evaluating a candidate's URL shortener design.
Analyze both the figure (Excalidraw diagram) and the candidate's explanation.

Evaluate based on URL Shortener HLD (High-Level Design) criteria:

1. **Core Functionality**:
   - URL encoding/decoding mechanism (hash function, base62/base64, etc.)
   - Short URL generation and storage
   - Original URL retrieval and redirection

2. **System Architecture**:
   - API design (RESTful endpoints)
   - Database schema and data modeling
   - Caching strategy (for frequently accessed URLs)
   - Load balancing and horizontal scaling

3. **Scalability**:
   - Handling high write throughput (URL creation)
   - Handling high read throughput (URL redirection)
   - Database partitioning/sharding strategy
   - CDN usage for static content

4. **Reliability & Performance**:
   - Fault tolerance and redundancy
   - Rate limiting and abuse prevention
   - Monitoring and observability
   - Error handling and edge cases

5. **Design Quality**:
   - Diagram clarity and component labeling
   - Consistency between diagram and explanation
   - Consideration of trade-offs
   - Edge case handling (expired URLs, custom URLs, collisions)

Provide constructive, conversational feedback. Be friendly and encouraging, like you're helping them improve.
Reference specific components from their diagram naturally."""

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

Evaluate this URL shortener design on the following rubric (1-5 scale):
1. **Core Functionality**: URL encoding/decoding, short URL generation, redirection logic
2. **Architecture**: Component selection, API design, database schema, system organization
3. **Scalability**: Handling high read/write throughput, partitioning, horizontal scaling, caching strategy
4. **Reliability**: Fault tolerance, redundancy, error handling, rate limiting
5. **Design Quality**: Diagram clarity, explanation quality, trade-off considerations, edge case handling

IMPORTANT: 
- Reference specific components from the diagram naturally in your feedback
- Be conversational and friendly - write like you're giving feedback to a colleague
- Focus on the most critical aspects for a URL shortener system
- Keep feedback concise but helpful (2-3 sentences)

The entire canvas has been analyzed ({total_components} components, {total_connections} connections).

Provide your response as JSON:
{{
  "scores": {{
    "core_functionality": 3.5,
    "architecture": 3.0,
    "scalability": 2.5,
    "reliability": 3.0,
    "design_quality": 4.0
  }},
  "feedback": "I like how you've set up the API and database layers - that's a solid foundation. I noticed you have a cache in your diagram which is great for handling those frequent redirect requests. One thing to think about: how would you handle the case where someone tries to shorten the same URL multiple times? Also, I don't see any rate limiting - that might be worth considering to prevent abuse.",
  "follow_up": "I see you're using a hash function for URL encoding. What happens if you get a collision, and how would you handle that?"
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
            "max_tokens": 150  # Reduced to work within credit limits (concise responses)
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
    
    async def generate_final_report(self, session: Session) -> Dict[str, Any]:
        """Generate final evaluation report for the session"""
        if not session.evaluations:
            return {
                "message": "No evaluations available",
                "scores": {},
                "timeline": []
            }
        
        # Aggregate scores
        all_scores = {}
        for eval_obj in session.evaluations:
            for key, value in eval_obj.scores.items():
                if key not in all_scores:
                    all_scores[key] = []
                all_scores[key].append(value)
        
        # Calculate averages
        avg_scores = {
            key: sum(values) / len(values)
            for key, values in all_scores.items()
        }
        
        # Build timeline
        timeline = []
        for i, eval_obj in enumerate(session.evaluations):
            timeline.append({
                "version": eval_obj.version,
                "scores": eval_obj.scores,
                "feedback": eval_obj.feedback,
                "follow_up": eval_obj.follow_up
            })
        
        # Generate summary
        lowest_score_key = min(avg_scores.items(), key=lambda x: x[1])[0] if avg_scores else None
        
        return {
            "session_id": session.session_id,
            "question": session.question_text,
            "average_scores": avg_scores,
            "timeline": timeline,
            "total_versions": len(session.canvas_versions),
            "total_messages": len(session.chat_history),
            "lowest_area": lowest_score_key,
            "suggested_learning": self._get_learning_suggestions(avg_scores)
        }
    
    def _get_learning_suggestions(self, scores: Dict[str, float]) -> List[str]:
        """Generate learning suggestions based on scores"""
        suggestions = []
        
        if scores.get("scalability", 5) < 3:
            suggestions.append("Study horizontal scaling patterns, load balancing strategies, and database partitioning for URL shorteners")
        
        if scores.get("reliability", 5) < 3:
            suggestions.append("Learn about redundancy, failover mechanisms, rate limiting, and distributed system resilience")
        
        if scores.get("architecture", 5) < 3:
            suggestions.append("Review RESTful API design, database schema for URL mapping, and system organization patterns")
        
        if scores.get("core_functionality", 5) < 3:
            suggestions.append("Focus on URL encoding/decoding mechanisms (hash functions, base62/base64), short URL generation, and redirection logic")
        
        if scores.get("design_quality", 5) < 3:
            suggestions.append("Improve diagram clarity, consider edge cases (expired URLs, custom URLs, collisions), and practice explaining trade-offs")
        
        return suggestions if suggestions else ["Continue practicing system design problems"]

