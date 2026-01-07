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
    
    def _classify_question_type(self, message: str) -> str:
        """Classify question type to determine response strategy."""
        message_lower = message.lower()
        
        # Methodology questions - need structure/frameworks
        methodology_keywords = [
            "functional requirement",
            "non-functional requirement",
            "non functional requirement",
            "what should i consider",
            "how do i approach",
            "what is the process",
            "what are the steps",
            "where do i start",
            "how do i begin"
        ]
        if any(keyword in message_lower for keyword in methodology_keywords):
            return "methodology"
        
        # Design questions - use Socratic method
        design_keywords = [
            "how should i design",
            "what technology",
            "should i use",
            "which approach",
            "how would you",
            "what design"
        ]
        if any(keyword in message_lower for keyword in design_keywords):
            return "design"
        
        # Stuck/confused - provide hints
        stuck_keywords = [
            "i don't know",
            "i'm stuck",
            "help me",
            "not sure",
            "confused",
            "can't figure out",
            "unclear"
        ]
        if any(keyword in message_lower for keyword in stuck_keywords):
            return "stuck"
        
        # Good question - acknowledge and guide
        if message_lower.endswith("?"):
            return "clarification"
        
        return "general"
    
    def _get_methodology_framework(
        self, 
        message: str, 
        question_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Provide scaffolding frameworks for methodology questions."""
        message_lower = message.lower()
        
        # Determine if asking about functional, non-functional, or both
        has_functional = "functional requirement" in message_lower and "non-functional" not in message_lower and "non functional" not in message_lower
        has_non_functional = "non-functional requirement" in message_lower or "non functional requirement" in message_lower
        has_both = ("functional" in message_lower and "non-functional" in message_lower) or ("functional" in message_lower and "non functional" in message_lower)
        
        # Try to get from question metadata first
        if question_metadata:
            if has_functional and question_metadata.get("functional_requirements_template"):
                return question_metadata["functional_requirements_template"]
            if has_non_functional and question_metadata.get("non_functional_requirements_template"):
                return question_metadata["non_functional_requirements_template"]
            if has_both:
                # Combine both templates
                func_template = question_metadata.get("functional_requirements_template", "")
                nfr_template = question_metadata.get("non_functional_requirements_template", "")
                if func_template and nfr_template:
                    return f"{func_template}\n\n{nfr_template}"
        
        # Fallback to generic frameworks
        functional_framework = """
Great question! Functional requirements describe WHAT the system should do.
Think about:
- User actions (what can users do?)
- Data operations (what data needs to be stored/retrieved?)
- System behaviors (how should the system respond?)
- Integrations (what external systems does it interact with?)

For this system, what user actions come to mind?
"""
        
        non_functional_framework = """
Excellent! Non-functional requirements describe HOW WELL the system should perform.
Consider:
- Performance (latency, throughput)
- Scalability (can it handle growth?)
- Reliability (uptime, fault tolerance)
- Security (authentication, encryption)
- Maintainability (code quality, monitoring)

For this system, which of these do you think is most critical?
"""
        
        if has_both:
            return f"{functional_framework}\n\n{non_functional_framework}"
        elif has_functional:
            return functional_framework
        elif has_non_functional:
            return non_functional_framework
        
        return ""
    
    def _acknowledge_good_question(self, message: str) -> str:
        """Acknowledge when candidate asks good questions."""
        message_lower = message.lower()
        
        good_question_patterns = [
            ("functional requirements", "That's exactly the right question! You're thinking about what the system needs to do."),
            ("non-functional requirements", "Perfect! You're considering how well the system should perform."),
            ("scalability", "Great thinking! Scalability is crucial for this type of system."),
            ("trade-off", "Excellent! Considering trade-offs shows strong system design thinking."),
            ("reliability", "That's a great question! Reliability is a key non-functional requirement."),
            ("performance", "Good question! Performance is critical for user experience.")
        ]
        
        for pattern, acknowledgment in good_question_patterns:
            if pattern in message_lower:
                return acknowledgment
        
        return ""
    
    def _check_repetition(self, chat_history: List[ChatMessage], current_message: str) -> Dict[str, Any]:
        """Check if candidate is asking similar questions repeatedly."""
        if len(chat_history) < 2:
            return {"is_repetitive": False, "count": 0, "escalate_help": False}
        
        # Check last 5 user messages for similar patterns
        recent_user_messages = [msg.content.lower() for msg in chat_history[-5:] if msg.role == "user"]
        current_lower = current_message.lower()
        
        # Count similar questions
        similar_keywords = ["requirement", "should", "how", "what", "approach", "design"]
        similar_count = sum(1 for msg in recent_user_messages
                           if any(keyword in msg and keyword in current_lower
                                 for keyword in similar_keywords))
        
        return {
            "is_repetitive": similar_count >= 2,
            "count": similar_count,
            "escalate_help": similar_count >= 3
        }
    
    def _analyze_candidate_state(
        self, 
        chat_history: List[ChatMessage], 
        canvas_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze candidate's current state and needs."""
        state = {
            "is_stuck": False,
            "needs_scaffolding": False,
            "is_making_progress": False,
            "confidence_level": "medium"
        }
        
        # Check for stuck indicators
        if chat_history:
            recent_messages = [msg.content.lower() for msg in chat_history[-3:] if msg.role == "user"]
            stuck_indicators = ["don't know", "stuck", "confused", "help", "not sure", "can't figure out"]
            if any(indicator in msg for msg in recent_messages for indicator in stuck_indicators):
                state["is_stuck"] = True
                state["needs_scaffolding"] = True
        
        # Check for progress
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            if parsed["component_count"] > 0:
                state["is_making_progress"] = True
        
        # Check confidence (based on question quality and specificity)
        if chat_history:
            last_user_msg = chat_history[-1].content.lower() if chat_history[-1].role == "user" else ""
            specific_questions = ["how", "what", "should", "consider", "approach"]
            if any(keyword in last_user_msg for keyword in specific_questions):
                state["confidence_level"] = "high"
        
        return state
    
    def _track_question_progression(
        self, 
        session: Session, 
        current_message: str
    ) -> Dict[str, Any]:
        """Track question patterns and determine if help should escalate."""
        progression = {
            "similar_questions_count": 0,
            "should_escalate": False,
            "help_level": "hint"  # hint -> guidance -> direct_structure
        }
        
        # Track similar questions in session
        if not hasattr(session, 'question_patterns'):
            session.question_patterns = {}
        
        # Extract question topic
        message_lower = current_message.lower()
        question_key = None
        if "functional" in message_lower or "requirement" in message_lower:
            question_key = "requirements"
        elif "non-functional" in message_lower or "nfr" in message_lower:
            question_key = "nfr"
        elif "design" in message_lower or "how should" in message_lower:
            question_key = "design"
        else:
            question_key = "general"
        
        if question_key in session.question_patterns:
            session.question_patterns[question_key] += 1
        else:
            session.question_patterns[question_key] = 1
        
        count = session.question_patterns[question_key]
        progression["similar_questions_count"] = count
        
        # Escalate help based on count
        if count >= 3:
            progression["should_escalate"] = True
            progression["help_level"] = "direct_structure"
        elif count >= 2:
            progression["should_escalate"] = True
            progression["help_level"] = "guidance"
        
        return progression
    
    def _get_relevant_evaluation_criteria(
        self, 
        message: str, 
        canvas_data: Optional[Dict[str, Any]],
        question_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Extract relevant evaluation criteria based on question."""
        message_lower = message.lower()
        criteria_context = ""
        
        # Use guidance_prompts from question_metadata if available
        if question_metadata and question_metadata.get("guidance_prompts"):
            guidance = question_metadata["guidance_prompts"]
            
            if "functional" in message_lower or "requirement" in message_lower:
                if guidance.get("core_functionality"):
                    criteria_context = f"""
Evaluation Criteria Context:
- Core Functionality: {', '.join(guidance.get('core_functionality', [])[:3])}
- This is what you're asking about! Think about what the system must do.
"""
            elif "non-functional" in message_lower or "performance" in message_lower or "scalability" in message_lower:
                if guidance.get("scalability") or guidance.get("reliability"):
                    criteria_context = f"""
Evaluation Criteria Context:
- Scalability: {', '.join(guidance.get('scalability', [])[:2]) if guidance.get('scalability') else 'Can the system handle growth?'}
- Reliability: {', '.join(guidance.get('reliability', [])[:2]) if guidance.get('reliability') else 'Fault tolerance, redundancy, monitoring'}
"""
        
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            if parsed["component_count"] > 0:
                criteria_context += f"""
- Architecture: Your current design has {parsed['component_count']} components
- Design Quality: Consider edge cases and trade-offs in your design
"""
        
        return criteria_context
    
    def _determine_response_strategy(
        self,
        question_type: str,
        candidate_state: Dict[str, Any],
        progression: Dict[str, Any]
    ) -> str:
        """Determine the right balance of guidance vs discovery."""
        
        # Methodology questions → Provide structure
        if question_type == "methodology":
            if progression["help_level"] == "direct_structure":
                return "provide_framework_with_examples"
            else:
                return "provide_framework_ask_application"
        
        # Stuck candidates → Provide hints
        if candidate_state["is_stuck"]:
            if progression["should_escalate"]:
                return "provide_structured_guidance"
            else:
                return "provide_hints"
        
        # Design questions → Socratic method
        if question_type == "design":
            return "socratic_questions"
        
        # Good questions → Acknowledge and guide
        if question_type == "clarification":
            return "acknowledge_and_guide"
        
        return "balanced_guidance"  # Default: mix of guidance and questions
    
    async def generate_response(
        self,
        message: str,
        canvas_data: Optional[Dict[str, Any]],
        chat_history: List[ChatMessage],
        question_text: str,
        question_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate AI interviewer response with adaptive strategy"""
        
        # Step 1: Classify question type
        question_type = self._classify_question_type(message)
        
        # Step 2: Analyze candidate state
        candidate_state = self._analyze_candidate_state(chat_history, canvas_data)
        
        # Step 3: Check for repetition
        repetition_info = self._check_repetition(chat_history, message)
        
        # Step 4: Track progression (requires session - will be passed separately)
        # For now, use repetition_info as proxy
        
        # Step 5: Determine response strategy
        response_strategy = self._determine_response_strategy(
            question_type, 
            candidate_state, 
            {
                "should_escalate": repetition_info["escalate_help"],
                "help_level": "direct_structure" if repetition_info["escalate_help"] else "hint"
            }
        )
        
        # Step 6: Build context (increased from 3 to 6 messages)
        context_parts = [f"Interview Question: {question_text}"]
        
        # Add canvas context if available
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            graph_summary = self.parser.get_graph_summary(parsed)
            context_parts.append(f"\nCurrent Diagram:\n{graph_summary}")
        
        # Add recent chat history (increased from 3 to 6 messages)
        if chat_history:
            context_parts.append("\nRecent Conversation:")
            for msg in chat_history[-6:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                context_parts.append(f"{role_label}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        # Step 7: Get evaluation criteria context
        criteria_context = self._get_relevant_evaluation_criteria(message, canvas_data, question_metadata)
        
        # Step 8: Route to appropriate handler based on strategy
        if response_strategy in ["provide_framework_ask_application", "provide_framework_with_examples"]:
            return await self._handle_methodology_question(
                message, question_type, chat_history, question_metadata, 
                repetition_info, criteria_context
            )
        elif response_strategy in ["provide_hints", "provide_structured_guidance"]:
            return await self._handle_stuck_candidate(
                message, chat_history, question_metadata, repetition_info, criteria_context
            )
        elif response_strategy == "socratic_questions":
            return await self._handle_design_question(
                message, canvas_data, chat_history, question_text, 
                question_metadata, criteria_context
            )
        else:
            return await self._handle_general_question(
                message, canvas_data, chat_history, question_text, 
                question_metadata, criteria_context
            )
    
    async def _handle_methodology_question(
        self,
        message: str,
        question_type: str,
        chat_history: List[ChatMessage],
        question_metadata: Optional[Dict[str, Any]],
        repetition_info: Dict[str, Any],
        criteria_context: str
    ) -> str:
        """Handle methodology questions with scaffolding."""
        acknowledgment = self._acknowledge_good_question(message)
        framework = self._get_methodology_framework(message, question_metadata)  # Pass actual message, not question_type
        
        # Build context
        context_parts = []
        if chat_history:
            context_parts.append("Recent Conversation:")
            for msg in chat_history[-6:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                context_parts.append(f"{role_label}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        # Determine prompt based on escalation level
        if repetition_info["escalate_help"]:
            # Provide framework with examples
            system_prompt = """You are a friendly system design interviewer. The candidate has asked similar methodology questions multiple times.
IMPORTANT: You MUST provide the framework/structure that is given below. Do not just ask them to think - provide the actual framework first, then ask them to apply it.

The framework below contains the structure they need. Present it clearly, then ask them to apply it to their specific problem."""
            
            user_prompt = f"""{context}

Candidate asked: {message}

{acknowledgment}

FRAMEWORK TO PROVIDE (you MUST include this in your response):
{framework}

{criteria_context}

The candidate has asked similar questions {repetition_info['count']} times. 
Your response MUST:
1. Start with the acknowledgment (if provided)
2. Present the framework above clearly and completely
3. Then ask them to apply it to their specific problem

Do NOT just ask them to think - provide the framework first!"""
        else:
            # Provide framework, ask application
            system_prompt = """You are a friendly system design interviewer. The candidate asked a methodology question.
IMPORTANT: You MUST provide the framework/structure that is given below. Do not just ask them to think - provide the actual framework first, then ask them to apply it.

The framework below contains the structure they need. Present it clearly, then ask them to think through how it applies to their specific problem."""
            
            user_prompt = f"""{context}

Candidate asked: {message}

{acknowledgment}

FRAMEWORK TO PROVIDE (you MUST include this in your response):
{framework}

{criteria_context}

Your response MUST:
1. Start with the acknowledgment (if provided)
2. Present the framework above clearly and completely
3. Then ask them to think through how it applies to their specific problem

Do NOT just ask them to think - provide the framework first!"""
        
        return await self._call_llm_with_error_handling(system_prompt, user_prompt)
    
    async def _handle_stuck_candidate(
        self,
        message: str,
        chat_history: List[ChatMessage],
        question_metadata: Optional[Dict[str, Any]],
        repetition_info: Dict[str, Any],
        criteria_context: str
    ) -> str:
        """Handle stuck/confused candidates with hints or structured guidance."""
        
        # Get hints from question_metadata if available
        hints = ""
        if question_metadata and question_metadata.get("hints"):
            hints_dict = question_metadata["hints"]
            # Get level 1 hint (most basic)
            if hints_dict.get("level_1"):
                hints = "\n".join(hints_dict["level_1"][:2])  # First 2 hints
        
        # Build context
        context_parts = []
        if chat_history:
            context_parts.append("Recent Conversation:")
            for msg in chat_history[-6:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                context_parts.append(f"{role_label}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        if repetition_info["escalate_help"]:
            # Provide structured guidance
            system_prompt = """You are a friendly system design interviewer. The candidate is stuck and has asked for help multiple times.
Provide structured guidance with clear steps or categories to help them move forward.
Be supportive and encouraging while giving them a clear path forward."""
            
            user_prompt = f"""{context}

Candidate said: {message}

The candidate is stuck and has asked similar questions {repetition_info['count']} times.
{hints}
{criteria_context}

Provide structured guidance with clear steps to help them move forward."""
        else:
            # Provide hints
            system_prompt = """You are a friendly system design interviewer. The candidate seems stuck or confused.
Provide helpful hints that guide them toward the answer without giving it directly.
Be encouraging and supportive."""
            
            user_prompt = f"""{context}

Candidate said: {message}

The candidate seems stuck or confused.
{hints}
{criteria_context}

Provide helpful hints that guide them toward the answer."""
        
        return await self._call_llm_with_error_handling(system_prompt, user_prompt)
    
    async def _handle_design_question(
        self,
        message: str,
        canvas_data: Optional[Dict[str, Any]],
        chat_history: List[ChatMessage],
        question_text: str,
        question_metadata: Optional[Dict[str, Any]],
        criteria_context: str
    ) -> str:
        """Handle design questions using Socratic method."""
        
        # Build context
        context_parts = [f"Interview Question: {question_text}"]
        
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            graph_summary = self.parser.get_graph_summary(parsed)
            context_parts.append(f"\nCurrent Diagram:\n{graph_summary}")
        
        if chat_history:
            context_parts.append("\nRecent Conversation:")
            for msg in chat_history[-6:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                context_parts.append(f"{role_label}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        system_prompt = """You are a friendly, experienced system design interviewer conducting a Socratic-style interview.
Your role is to GUIDE the candidate through questions, NOT to provide direct answers.

CRITICAL RULES:
1. NEVER give direct answers to design questions - always ask clarifying questions instead
2. When the candidate asks "what technology should I use?" or "how should I design X?", respond with questions like:
   - "What do you think would be a good approach for X? What factors would you consider?"
   - "Let's think about this together - what are the trade-offs you're considering?"
   - "That's a great question. What requirements would influence your decision about Y?"
3. Guide them through the evaluation criteria by asking questions about:
   - System architecture (API design, database schema, caching, load balancing)
   - Scalability (read/write throughput, partitioning, horizontal scaling)
   - Reliability (fault tolerance, redundancy, rate limiting, monitoring)
   - Design quality (diagram clarity, edge cases, trade-offs)
4. Be conversational, warm, and encouraging - like a mentor
5. Keep responses concise (2-3 sentences, usually ending with a question)
6. Reference their diagram when relevant: "I see you've drawn X - can you explain how that handles Y?"

IMPORTANT: Your job is to help them discover the answers through questions, not to tell them the answers."""
        
        user_prompt = f"""{context}

Candidate: {message}

{criteria_context}

Respond as the interviewer using the Socratic method:
- DO NOT answer the design question directly. Instead, ask clarifying questions that guide them to think through the answer themselves.
- Guide them through the evaluation criteria by asking questions about architecture, scalability, reliability, and design quality.
- Keep it conversational and friendly, but always guide through questions, never give direct answers.

Remember: You are helping them discover answers through questions, not providing answers directly."""
        
        return await self._call_llm_with_error_handling(system_prompt, user_prompt, temperature=0.5)
    
    async def _handle_general_question(
        self,
        message: str,
        canvas_data: Optional[Dict[str, Any]],
        chat_history: List[ChatMessage],
        question_text: str,
        question_metadata: Optional[Dict[str, Any]],
        criteria_context: str
    ) -> str:
        """Handle general questions with balanced guidance."""
        
        acknowledgment = self._acknowledge_good_question(message)
        
        # Build context
        context_parts = [f"Interview Question: {question_text}"]
        
        if canvas_data:
            parsed = self.parser.parse(canvas_data)
            graph_summary = self.parser.get_graph_summary(parsed)
            context_parts.append(f"\nCurrent Diagram:\n{graph_summary}")
        
        if chat_history:
            context_parts.append("\nRecent Conversation:")
            for msg in chat_history[-6:]:
                role_label = "Candidate" if msg.role == "user" else "Interviewer"
                context_parts.append(f"{role_label}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        system_prompt = """You are a friendly, experienced system design interviewer.
Your role is to GUIDE the candidate through questions, balancing between providing helpful context and asking them to think.

CRITICAL RULES:
1. Acknowledge good questions when appropriate
2. Provide helpful context when needed, but still ask follow-up questions
3. Guide them through the evaluation criteria
4. Be conversational, warm, and encouraging
5. Keep responses concise (2-3 sentences)
6. Reference their diagram when relevant

IMPORTANT: Balance between guidance and discovery - provide context when helpful, but still encourage them to think through the answer."""
        
        user_prompt = f"""{context}

Candidate: {message}

{acknowledgment}
{criteria_context}

Respond as the interviewer with balanced guidance:
- Acknowledge good questions when appropriate
- Provide helpful context, but still ask follow-up questions
- Guide them through the evaluation criteria
- Keep it conversational and friendly"""
        
        return await self._call_llm_with_error_handling(system_prompt, user_prompt, temperature=0.6)
    
    async def _call_llm_with_error_handling(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 400
    ) -> str:
        """Helper method to call LLM with error handling and guardrails."""
        if not self.llm:
            return "I'm here to help, but the API key is not configured. Please set LLM_PROVIDER and API key in your environment."
        
        # Sanitize inputs
        sanitized_message, is_safe, warning = guardrails.sanitize_input(user_prompt)
        if not is_safe:
            print(f"[GUARDRAIL] User message flagged: {warning}")
        
        # Apply guardrails to prompts
        sanitized_system, sanitized_user, prompt_is_safe = guardrails.validate_and_sanitize_prompt(
            system_prompt, sanitized_message
        )
        
        try:
            messages = [
                LLMMessage(role="system", content=sanitized_system),
                LLMMessage(role="user", content=sanitized_user)
            ]
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=temperature,  # Reduced from 0.7 for more consistent responses
                max_tokens=max_tokens  # Increased from 200 for more complete responses
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
            
            if is_significant:
                # Check if user has been idle for 3 seconds AFTER the significant change
                # last_drawing_activity_time was set when the significant change was detected
                if session.last_drawing_activity_time:
                    idle_time = current_time - session.last_drawing_activity_time
                    
                    if idle_time >= 3:  # 3 seconds idle after significant change (reduced from 10s for faster response)
                        # Use a more specific prompt key based on the change timestamp
                        prompt_key = f"canvas_change_{int(session.last_drawing_activity_time)}"
                        
                        if prompt_key not in session.prompt_history:
                            prompt = await self._generate_figure_aware_prompt(session)
                            if prompt:
                                session.prompt_history.append(prompt_key)
                                session.last_prompt_time = current_time
                                # Clear previous_canvas after triggering to allow detection of next significant change
                                import copy
                                session.previous_canvas = copy.deepcopy(session.current_canvas) if session.current_canvas else None
                                print(f"[TRIGGER] Event-Driven prompt triggered: {idle_time:.1f}s after significant change")
                                return prompt
                # No need to log when conditions aren't met - reduces noise
        # No canvas data available - skip logging to reduce noise
        
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
- Asks them a question about what they added IN THE CONTEXT OF THE SPECIFIC INTERVIEW QUESTION
- Your question must be directly relevant to solving the interview question provided
- NEVER ask about unrelated systems, features, or scenarios
- NEVER give direct answers or explanations
- Sound like you're genuinely interested in their progress

Write it like you're talking to a colleague, not a robot. Always end with a question."""
                    else:
                        # Standard prompt asking for explanation
                        system_prompt = """You're a friendly technical interviewer using the Socratic method. The candidate just added some new components or connections to their diagram.

Write a natural, conversational prompt (1-2 sentences) asking them a question about what they added.
- Be curious and encouraging, like you're genuinely interested
- Ask them to explain what they added and why (e.g., "I see you added X - can you walk me through how that works?" or "What was your reasoning for including Y?")
- CRITICALLY IMPORTANT: Your question must be directly relevant to the specific interview question provided
- Connect what they added to solving the actual problem they're working on
- NEVER ask about unrelated systems or scenarios not mentioned in the interview question
- NEVER provide explanations or answers yourself
- Sound like a real person having a conversation, not a formal evaluation

Keep it friendly and casual. Always end with a question."""
                
                user_prompt = f"""{context}

CRITICAL: The interview question above is "{session.question_text}". 
All prompts MUST be relevant to THIS specific question ONLY. Do not ask about other systems.

The candidate just added {new_components} new components and {new_connections} new connections to their diagram.
Generate a friendly prompt asking them to explain these changes IN THE CONTEXT OF the specific interview question above."""
                
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
- Your question must be relevant to the specific interview question they're solving
- NEVER provide the answer or explanation yourself
- Be friendly and non-confrontational, like you're just trying to understand their thinking
- Always end with a question"""
                
                user_prompt = f"""Interview Question: {session.question_text}

IMPORTANT: Keep your question relevant to THIS specific interview question.

The candidate mentioned {mismatch_text} in their explanation, but it's not visible in their current diagram.
Generate a clarifying question about this discrepancy that's relevant to the interview question."""
                
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
    
    async def _generate_milestone_prompt(self, session: Session, milestone_topic: str) -> Optional[str]:
        """Generate a milestone prompt that's specific to the interview question"""
        system_prompt = f"""You're a friendly technical interviewer using the Socratic method. The candidate has reached a milestone in their system design - they've added components related to {milestone_topic}.

Write a natural, encouraging prompt (2-3 sentences) that:
- Acknowledges their progress on {milestone_topic} in a positive way
- Asks a follow-up question that pushes them to think deeper about the SPECIFIC system they're designing
- Your question MUST be directly relevant to the interview question they're solving
- NEVER ask about unrelated systems or scenarios
- Be genuinely curious about their thinking
- Always end with a question

Keep it conversational and friendly."""

        user_prompt = f"""Interview Question: {session.question_text}

The candidate has just added {milestone_topic} components to their design. Generate an encouraging follow-up question that:
1. Is SPECIFIC to the interview question above (not generic)
2. Helps them think deeper about {milestone_topic} in the context of THIS specific system
3. Encourages them to consider edge cases or next steps relevant to THIS problem"""

        try:
            # Apply guardrails to prompts
            sanitized_system, sanitized_user, _ = guardrails.validate_and_sanitize_prompt(system_prompt, user_prompt)
            response = await self._call_api(sanitized_system, sanitized_user)
            if response:
                sanitized_response, _, _ = guardrails.sanitize_input(response)
                return sanitized_response
            else:
                # Fallback to generic prompt if API fails
                return f"Great work on adding {milestone_topic}! How does this fit into solving the overall problem? What edge cases should we consider?"
        except:
            return f"Nice progress on {milestone_topic}! Can you walk me through how this helps solve the problem?"
    
    async def _check_milestones(self, session: Session) -> Optional[str]:
        """Check if candidate reached a new milestone (DISABLED)"""
        # TEMPORARILY DISABLED: Milestone prompts causing spam
        # TODO: Re-enable with proper rate limiting and deduplication
        return None
        
        # Original code below - kept for reference
        # if not session.current_canvas:
        #     return None
        # 
        # parsed = self.parser.parse(session.current_canvas)
        # labels = " ".join([label.lower() for label in parsed["labels"].values()])
        # 
        # # Check milestones
        # milestones_to_check = {
        #     "scaling_components": {
        #         "keywords": ["load balancer", "lb", "horizontal", "scale"],
        #         "milestone": "scaling_discussed",
        #         "topic": "scaling and load balancing"
        #     },
        #     "reliability_components": {
        #         "keywords": ["replica", "failover", "backup", "redundancy"],
        #         "milestone": "reliability_discussed",
        #         "topic": "redundancy and reliability"
        #     },
        #     "architecture_complete": {
        #         "keywords": ["api", "service", "database", "cache"],
        #         "milestone": "architecture_complete",
        #         "topic": "core architecture"
        #     }
        # }
        # 
        # for milestone_name, milestone_data in milestones_to_check.items():
        #     if session.milestones.get(milestone_data["milestone"], False):
        #         continue  # Already reached this milestone
        #     
        #     # Check if milestone keywords are present
        #     if any(keyword in labels for keyword in milestone_data["keywords"]):
        #         # Check if we have enough components (at least 3-4)
        #         if parsed["component_count"] >= 3:
        #             session.milestones[milestone_data["milestone"]] = True
        #             prompt_key = f"milestone_{milestone_name}"
        #             if prompt_key not in session.prompt_history:
        #                 # Generate context-aware prompt using LLM
        #                 prompt = await self._generate_milestone_prompt(session, milestone_data["topic"])
        #                 if prompt:
        #                     session.prompt_history.append(prompt_key)
        #                     return prompt
        # 
        # return None
    
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

