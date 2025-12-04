"""
Conversation Orchestrator - determines when and how the AI should respond
"""
import time
from typing import Dict, Any, List, Optional, Tuple
import json
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage
from core.config import settings
from utils.system_design.models import Session, ChatMessage
from utils.system_design.canvas_parser import CanvasParser
from utils.system_design.guardrails import guardrails


class ConversationOrchestrator:
    """Manages conversation flow and AI response triggers"""
    
    def __init__(self):
        self.parser = CanvasParser()
        
        # Use factory to get LLM provider with configured model
        try:
            self.llm = LLMProviderFactory.create_provider()
            self.model = self.llm.model  # Store the actual model being used
        except ValueError as e:
            print(f"WARNING: {str(e)}")
            print("LLM responses will not work. Please set LLM_PROVIDER and API key in your environment or .env file")
            self.llm = None
            self.model = None
    
    def should_respond(self, message: str, session: Session) -> bool:
        """
        Determine if AI should respond based on message intent
        Returns True if message is a question, greeting, or explicit request
        """
        message_lower = message.lower().strip()
        
        # Always respond to greetings
        greetings = ["hi", "hello", "hey", "greetings"]
        if any(greeting in message_lower for greeting in greetings):
            return True
        
        # Explicit triggers
        triggers = [
            "please review",
            "can you review",
            "what do you think",
            "feedback",
            "evaluate",
            "review",
            "help"
        ]
        
        # Respond to questions (ends with ?) or contains trigger words
        if message_lower.endswith("?") or any(trigger in message_lower for trigger in triggers):
            return True
        
        # Respond to messages that seem like explanations or requests
        # (messages longer than 10 chars are likely explanations)
        if len(message_lower) > 10:
            return True
        
        return False
    
    async def generate_response(
        self,
        message: str,
        canvas_data: Optional[Dict[str, Any]],
        chat_history: List[ChatMessage],
        question_text: str
    ) -> str:
        """Generate AI interviewer response"""
        
        # Build context
        context_parts = [f"Interview Question: {question_text}"]
        
        # Add canvas context if available
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            graph_summary = self.parser.get_graph_summary(parsed)
            context_parts.append(f"\nCurrent Diagram:\n{graph_summary}")
        
        # Add recent chat history
        if chat_history:
            context_parts.append("\nRecent Conversation:")
            for msg in chat_history[-3:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                context_parts.append(f"{role_label}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        system_prompt = """You are a friendly, experienced system design interviewer conducting a Socratic-style interview with a candidate.
Your role is to GUIDE the candidate through questions, NOT to provide direct answers.

CRITICAL RULES:
1. NEVER give direct answers to questions - always ask clarifying questions instead
2. When the candidate asks "what should X be?" or "how should I do Y?", respond with questions like:
   - "What do you think would be a good approach for X?"
   - "Let's think about this together - what are the trade-offs you're considering?"
   - "That's a great question. What factors would influence your decision about Y?"
3. Guide them through the evaluation criteria by asking questions about:
   - Core functionality (URL encoding/decoding, generation, redirection)
   - System architecture (API design, database schema, caching, load balancing)
   - Scalability (read/write throughput, partitioning, horizontal scaling)
   - Reliability (fault tolerance, redundancy, rate limiting, monitoring)
   - Design quality (diagram clarity, edge cases, trade-offs)
4. Be conversational, warm, and encouraging - like a mentor
5. Keep responses concise (2-3 sentences, usually ending with a question)
6. Reference their diagram when relevant: "I see you've drawn X - can you explain how that handles Y?"

IMPORTANT: Your job is to help them discover the answers through questions, not to tell them the answers.
If they ask for requirements or specifications, ask them what they think the requirements should be based on the problem statement."""

        # Sanitize user message and chat history
        sanitized_message, is_safe, warning = guardrails.sanitize_input(message)
        if not is_safe:
            print(f"[GUARDRAIL] User message flagged: {warning}")
        
        # Sanitize chat history
        sanitized_history = guardrails.sanitize_chat_history(chat_history)
        
        # Rebuild context with sanitized data
        context_parts = [f"Interview Question: {question_text}"]
        
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            graph_summary = self.parser.get_graph_summary(parsed)
            context_parts.append(f"\nCurrent Diagram:\n{graph_summary}")
        
        if sanitized_history:
            context_parts.append("\nRecent Conversation:")
            for msg in sanitized_history[-3:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
                context_parts.append(f"{role_label}: {content}")
        
        context = "\n".join(context_parts)
        
        user_prompt = f"""{context}

Candidate: {sanitized_message}

Respond as the interviewer using the Socratic method:
- If the candidate asks a question, DO NOT answer it directly. Instead, ask them a clarifying question that guides them to think through the answer themselves.
- If they ask "what should X be?", respond with "What do you think X should be? What factors would you consider?"
- If they ask for requirements, ask them "Based on the problem statement, what requirements do you think we need to consider?"
- Guide them through the evaluation criteria (core functionality, architecture, scalability, reliability, design quality) by asking questions about each area.
- Keep it conversational and friendly, but always guide through questions, never give direct answers.

Remember: You are helping them discover answers through questions, not providing answers directly."""

        # Apply guardrails to prompts
        sanitized_system, sanitized_user, prompt_is_safe = guardrails.validate_and_sanitize_prompt(system_prompt, user_prompt)
        
        # Call LLM API
        if not self.llm:
            return "I'm here to help, but the API key is not configured. Please set LLM_PROVIDER and API key in your environment."
        
        try:
            messages = [
                LLMMessage(role="system", content=sanitized_system),
                LLMMessage(role="user", content=sanitized_user)
            ]
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=200  # Reduced to work within credit limits
            )
            
            content = response.content or "I understand. Please continue."
            print(f"LLM API response: {content[:100]}...")  # Log first 100 chars
            return content
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"LLM API error: {str(e)}")
            
            # Handle specific error types
            if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                print(f"LLM API 401 Unauthorized: Invalid API key")
                return "I'm here to help with your system design. However, there's a configuration issue. Please check your API key setting."
            elif "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                print(f"LLM API 429 Rate Limit: Too many requests")
                return "I'm here to help, but I'm receiving too many requests right now. Could you wait a moment and try again?"
            elif "400" in error_str or "bad request" in error_str:
                print(f"LLM API 400 Bad Request: {str(e)}")
                return "I'm having trouble processing that request. Could you rephrase your question? I'm here to help guide you through the system design."
            else:
                import traceback
                traceback.print_exc()
                return "I'm having trouble generating a response right now. Could you try rephrasing your question? I'm here to help guide you through the system design."
    
    def detect_significant_change(
        self,
        old_canvas: Optional[Dict[str, Any]],
        new_canvas: Dict[str, Any]
    ) -> bool:
        """Detect if canvas change is significant enough to trigger AI"""
        if not old_canvas:
            print(f"[DEBUG] detect_significant_change: old_canvas is None, returning False")
            return False
        
        old_parsed = self.parser.parse(old_canvas)
        new_parsed = self.parser.parse(new_canvas)
        
        # Significant if:
        # - Added 3+ new components
        # - Added first connection
        # - Added labeled component (cache, queue, etc.)
        
        component_diff = new_parsed["component_count"] - old_parsed["component_count"]
        edge_diff = new_parsed["edge_count"] - old_parsed["edge_count"]
        
        print(f"[DEBUG] detect_significant_change: old_components={old_parsed['component_count']}, new_components={new_parsed['component_count']}, diff={component_diff}")
        print(f"[DEBUG] detect_significant_change: old_edges={old_parsed['edge_count']}, new_edges={new_parsed['edge_count']}, diff={edge_diff}")
        
        if component_diff >= 3:
            print(f"[DEBUG] ✅ Significant change: Added {component_diff} components (>=3)")
            return True
        
        if old_parsed["edge_count"] == 0 and edge_diff > 0:
            print(f"[DEBUG] ✅ Significant change: Added first connection")
            return True
        
        # Check for important labels
        important_labels = ["cache", "queue", "load balancer", "replica", "db", "database"]
        new_labels = new_parsed["labels"]
        old_labels = old_parsed["labels"]
        
        print(f"[DEBUG] detect_significant_change: old_labels={list(old_labels.values())}, new_labels={list(new_labels.values())}")
        
        for node_id, label in new_labels.items():
            if node_id not in old_labels:
                label_lower = label.lower()
                if any(important in label_lower for important in important_labels):
                    print(f"[DEBUG] ✅ Significant change: Added important label '{label}'")
                    return True
        
        print(f"[DEBUG] ❌ No significant change detected")
        return False
    
    async def check_proactive_prompts(self, session: Session) -> Optional[str]:
        """
        Check if any proactive prompts should be triggered.
        Returns prompt message if trigger conditions are met, None otherwise.
        Implements all 6 trigger types from the interview flow specification.
        """
        current_time = time.time()
        
        print(f"[TRIGGER CHECK] Starting proactive prompt check at {current_time}")
        
        # Update last activity if needed
        if session.last_activity_time is None:
            session.last_activity_time = current_time
        
        # Check non-idle-dependent prompts FIRST (these can trigger immediately)
        # 3️⃣ Evaluation-Triggered: Check latest evaluation for weak areas
        if session.evaluations:
            latest_eval = session.evaluations[-1]
            prompt = await self._check_evaluation_followup(session, latest_eval)
            if prompt:
                print(f"[TRIGGER] Evaluation-Triggered prompt: lowest score dimension")
                return prompt
        
        # 4️⃣ Uncertainty / Confidence-Based: Mismatch between figure and text
        if session.current_canvas and session.chat_history:
            prompt = await self._detect_figure_text_mismatch(session)
            if prompt:
                print(f"[TRIGGER] Mismatch detection prompt triggered")
                return prompt
        
        # 5️⃣ Rubric-Checkpoint: Milestone detection
        if session.current_canvas:
            prompt = await self._check_milestones(session)
            if prompt:
                print(f"[TRIGGER] Milestone checkpoint prompt triggered")
                return prompt
        
        # 2️⃣ Event-Driven (Figure-Aware): Significant canvas change + idle for ≥3s
        if session.current_canvas and session.previous_canvas:
            # Check if there's a significant difference between previous_canvas and current_canvas
            is_significant = self.detect_significant_change(session.previous_canvas, session.current_canvas)
            print(f"[DEBUG] Event-Driven check: has_canvas=True, is_significant={is_significant}, last_drawing={session.last_drawing_activity_time}")
            print(f"[DEBUG] Event-Driven: previous_canvas components={self.parser.parse(session.previous_canvas)['component_count'] if session.previous_canvas else 0}, current_canvas components={self.parser.parse(session.current_canvas)['component_count'] if session.current_canvas else 0}")
            
            if is_significant:
                # Check if user has been idle for 3 seconds AFTER the significant change
                # last_drawing_activity_time was set when the significant change was detected
                if session.last_drawing_activity_time:
                    idle_time = current_time - session.last_drawing_activity_time
                    print(f"[DEBUG] Event-Driven: significant change detected, idle_time={idle_time:.1f}s since change (need >=3s)")
                    
                    if idle_time >= 3:  # 3 seconds idle after significant change (reduced from 10s for faster response)
                        # Use a more specific prompt key based on the change timestamp
                        prompt_key = f"canvas_change_{int(session.last_drawing_activity_time)}"
                        print(f"[DEBUG] Event-Driven: idle_time OK, prompt_key={prompt_key}, in_history={prompt_key in session.prompt_history}")
                        
                        if prompt_key not in session.prompt_history:
                            prompt = await self._generate_figure_aware_prompt(session)
                            print(f"[DEBUG] Event-Driven: generated prompt: {prompt[:50] if prompt else 'None'}...")
                            if prompt:
                                session.prompt_history.append(prompt_key)
                                session.last_prompt_time = current_time
                                # Clear previous_canvas after triggering to allow detection of next significant change
                                import copy
                                session.previous_canvas = copy.deepcopy(session.current_canvas) if session.current_canvas else None
                                print(f"[DEBUG] Reset previous_canvas after trigger (now has {self.parser.parse(session.previous_canvas)['component_count'] if session.previous_canvas else 0} components)")
                                print(f"[TRIGGER] Event-Driven prompt triggered: {idle_time:.1f}s after significant change")
                                return prompt
                            else:
                                print(f"[DEBUG] Event-Driven: prompt generation returned None")
                        else:
                            print(f"[DEBUG] Event-Driven: prompt already sent for this change")
                    else:
                        print(f"[DEBUG] Event-Driven: idle_time too short ({idle_time:.1f}s < 3s)")
                else:
                    print(f"[DEBUG] Event-Driven: last_drawing_activity_time not set, cannot check idle time")
            else:
                print(f"[DEBUG] Event-Driven: no significant change detected between previous and current canvas")
        else:
            print(f"[DEBUG] Event-Driven check: current_canvas={session.current_canvas is not None}, previous_canvas={session.previous_canvas is not None}")
        
        return None
    
    async def _generate_figure_aware_prompt(self, session: Session) -> Optional[str]:
        """Generate prompt after significant canvas change"""
        if not session.current_canvas:
            return None
        
        parsed = self.parser.parse(session.current_canvas)
        graph_summary = self.parser.get_graph_summary(parsed)
        
        # Find what was added
        if session.previous_canvas:
            old_parsed = self.parser.parse(session.previous_canvas)
            new_components = parsed["component_count"] - old_parsed["component_count"]
            new_connections = parsed["edge_count"] - old_parsed["edge_count"]
            
            if new_components > 0 or new_connections > 0:
                context = f"Interview Question: {session.question_text}\n\nRecent Diagram Changes:\n{graph_summary}"
                
                # Check if this is a follow-up to a previous question (recent AI message)
                has_recent_ai_message = False
                if session.chat_history:
                    last_ai_msg = None
                    for msg in reversed(session.chat_history[-5:]):
                        if msg.role == "assistant":
                            last_ai_msg = msg
                            break
                    if last_ai_msg:
                        # Check if AI asked a question recently (within last 2 minutes)
                        has_recent_ai_message = True
                
                    if has_recent_ai_message:
                        # More direct prompt suggesting evaluation
                        system_prompt = """You're a friendly technical interviewer using the Socratic method. The candidate just made some changes to their diagram, probably responding to your last question.
Write a natural, conversational prompt (1-2 sentences) that:
- Acknowledges what they added in a friendly way
- Asks them a question about what they added (e.g., "Can you explain how X works?" or "What was your thinking behind adding Y?")
- NEVER give direct answers or explanations
- Sound like you're genuinely interested in their progress

Write it like you're talking to a colleague, not a robot. Always end with a question."""
                    else:
                        # Standard prompt asking for explanation
                        system_prompt = """You're a friendly technical interviewer using the Socratic method. The candidate just added some new components or connections to their diagram.
Write a natural, conversational prompt (1-2 sentences) asking them a question about what they added.
- Be curious and encouraging, like you're genuinely interested
- Ask them to explain what they added and why (e.g., "I see you added X - can you walk me through how that works?" or "What was your reasoning for including Y?")
- NEVER provide explanations or answers yourself
- Sound like a real person having a conversation, not a formal evaluation

Keep it friendly and casual. Always end with a question."""
                
                user_prompt = f"""{context}

The candidate just added {new_components} new components and {new_connections} new connections to their diagram.
Generate a friendly prompt asking them to explain these changes."""
                
                try:
                    # Apply guardrails to prompts
                    sanitized_system, sanitized_user, _ = guardrails.validate_and_sanitize_prompt(system_prompt, user_prompt)
                    response = await self._call_api(sanitized_system, sanitized_user)
                    if response:
                        # Sanitize the response as well (in case LLM was manipulated)
                        sanitized_response, _, _ = guardrails.sanitize_input(response)
                        # Add hint about evaluation if this is a follow-up
                        if has_recent_ai_message and "submit" not in sanitized_response.lower() and "evaluate" not in sanitized_response.lower():
                            sanitized_response += " You can click 'Submit for Feedback' or type 'please evaluate' to get detailed feedback on your design."
                        return sanitized_response
                    else:
                        # API returned None (no API key), use fallback
                        if has_recent_ai_message:
                            return "I see you've added some new components! That's great progress. Want to walk me through what you added, or would you like to get some detailed feedback by clicking 'Submit for Feedback'?"
                        return "Nice! I see you've made some changes to your diagram. Can you tell me a bit about what you added and how these components work together?"
                except:
                    if has_recent_ai_message:
                        return "I see you've added some new components! That's great progress. Want to walk me through what you added, or would you like to get some detailed feedback by clicking 'Submit for Feedback'?"
                    return "Nice! I see you've made some changes to your diagram. Can you tell me a bit about what you added and how these components work together?"
        
        return None
    
    async def _check_evaluation_followup(self, session: Session, evaluation: Any) -> Optional[str]:
        """Check if evaluation suggests a follow-up question based on lowest score"""
        scores = evaluation.scores if hasattr(evaluation, 'scores') else evaluation.get('scores', {})
        if not scores:
            return None
        
        # Find lowest scoring dimension
        lowest_dimension = min(scores.items(), key=lambda x: x[1])
        dimension_name, score = lowest_dimension
        
        # Only prompt if score is low (< 3.0) and we haven't asked about this recently
        if score < 3.0:
            prompt_key = f"eval_followup_{dimension_name}"
            if prompt_key not in session.prompt_history:
                # Check if follow_up already exists in evaluation
                if hasattr(evaluation, 'follow_up') and evaluation.follow_up:
                    session.prompt_history.append(prompt_key)
                    return evaluation.follow_up
                elif evaluation.get('follow_up'):
                    session.prompt_history.append(prompt_key)
                    return evaluation.get('follow_up')
        
        return None
    
    async def _detect_figure_text_mismatch(self, session: Session) -> Optional[str]:
        """Detect mismatch between what's in the figure vs what's mentioned in chat"""
        if not session.current_canvas or not session.chat_history:
            return None
        
        # Get recent chat messages (last 5)
        recent_chat = " ".join([msg.content.lower() for msg in session.chat_history[-5:] if msg.role == "user"])
        
        # Parse canvas
        parsed = self.parser.parse(session.current_canvas)
        canvas_labels = " ".join([label.lower() for label in parsed["labels"].values()])
        
        # Check for common mismatches
        mismatches = []
        
        # Check for replication mentions without replicas in diagram
        if ("replica" in recent_chat or "replicate" in recent_chat) and "replica" not in canvas_labels:
            mismatches.append("replication")
        
        # Check for cache mentions without cache in diagram
        if ("cache" in recent_chat or "caching" in recent_chat) and "cache" not in canvas_labels and "redis" not in canvas_labels:
            mismatches.append("caching")
        
        # Check for load balancer mentions without LB in diagram
        if ("load balancer" in recent_chat or "load balancing" in recent_chat) and "load balancer" not in canvas_labels and "lb" not in canvas_labels:
            mismatches.append("load balancing")
        
        if mismatches:
            prompt_key = f"mismatch_{'_'.join(mismatches)}"
            if prompt_key not in session.prompt_history:
                mismatch_text = ", ".join(mismatches)
                system_prompt = """You're a friendly technical interviewer using the Socratic method. You noticed the candidate mentioned something in their explanation that doesn't show up in their diagram.
Write a natural, curious question (1-2 sentences) asking about this discrepancy.
- Ask them to clarify or explain the mismatch (e.g., "You mentioned X in your explanation, but I don't see it in your diagram. Can you help me understand - are you planning to add that?")
- NEVER provide the answer or explanation yourself
- Be friendly and non-confrontational, like you're just trying to understand their thinking
- Always end with a question"""
                
                user_prompt = f"""Interview Question: {session.question_text}
    
    The candidate mentioned {mismatch_text} in their explanation, but it's not visible in their current diagram.
    Generate a clarifying question about this."""
                
                try:
                    # Apply guardrails to prompts
                    sanitized_system, sanitized_user, _ = guardrails.validate_and_sanitize_prompt(system_prompt, user_prompt)
                    response = await self._call_api(sanitized_system, sanitized_user)
                    if response:
                        session.prompt_history.append(prompt_key)
                        return response
                    else:
                        # API returned None (no API key), use fallback
                        session.prompt_history.append(prompt_key)
                        return f"Interesting! You mentioned {mismatch_text} in your explanation, but I don't see it in your diagram. Can you help me understand - are you planning to add that, or did I miss something?"
                except:
                    session.prompt_history.append(prompt_key)
                    return f"Interesting! You mentioned {mismatch_text} in your explanation, but I don't see it in your diagram. Can you help me understand - are you planning to add that, or did I miss something?"
        
        return None
    
    async def _check_milestones(self, session: Session) -> Optional[str]:
        """Check if candidate reached a new milestone and should transition topics"""
        if not session.current_canvas:
            return None
        
        parsed = self.parser.parse(session.current_canvas)
        labels = " ".join([label.lower() for label in parsed["labels"].values()])
        
        # Check milestones
        milestones_to_check = {
            "scaling_components": {
                "keywords": ["load balancer", "lb", "horizontal", "scale"],
                "milestone": "scaling_discussed",
                "prompt": "Nice! I see you've added load balancing and scaling components. That's a smart move for handling traffic. One thing I'm curious about - how would you handle things if one of your data centers goes down? What's your plan for regional failures?"
            },
            "reliability_components": {
                "keywords": ["replica", "failover", "backup", "redundancy"],
                "milestone": "reliability_discussed",
                "prompt": "Great thinking on the redundancy! I can see you've got replicas and failover mechanisms in place. That's really important for a system like this. What about monitoring - how would you know if something's going wrong? Do you have any thoughts on observability?"
            },
            "architecture_complete": {
                "keywords": ["api", "service", "database", "cache"],
                "milestone": "architecture_complete",
                "prompt": "Your core architecture is looking really solid! You've got the main pieces in place. Now I'm wondering - what happens in edge cases? Like, what if someone tries to shorten a URL that's already been shortened? Or what if the original URL expires? How would you handle those scenarios?"
            }
        }
        
        for milestone_name, milestone_data in milestones_to_check.items():
            if session.milestones.get(milestone_data["milestone"], False):
                continue  # Already reached this milestone
            
            # Check if milestone keywords are present
            if any(keyword in labels for keyword in milestone_data["keywords"]):
                # Check if we have enough components (at least 3-4)
                if parsed["component_count"] >= 3:
                    session.milestones[milestone_data["milestone"]] = True
                    prompt_key = f"milestone_{milestone_name}"
                    if prompt_key not in session.prompt_history:
                        session.prompt_history.append(prompt_key)
                        return milestone_data["prompt"]
        
        return None
    
    async def _call_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Helper method to call LLM API for prompts"""
        if not self.llm:
            return None
        
        try:
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ]
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=100  # Reduced for prompts to work within credit limits
            )
            
            return response.content or ""
            
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                print(f"LLM API 401 Unauthorized: Invalid API key")
            elif "429" in error_str or "rate limit" in error_str:
                print(f"LLM API 429 Rate Limit: Too many requests")
            else:
                print(f"LLM API error: {str(e)}")
            return None

