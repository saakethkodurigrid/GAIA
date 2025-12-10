"""
Interview Analysis Summary Generator
Generates a comprehensive 4-line summary of interview performance using LLM.
"""
from typing import Dict, Any, Optional
import logging
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage

logger = logging.getLogger(__name__)


async def generate_interview_summary(
    mcq_metadata: Dict[str, Any],
    coding_metadata: Dict[str, Any],
    system_design_metadata: Dict[str, Any],
    integrity_metadata: Dict[str, Any]
) -> str:
    """
    Generate a comprehensive 4-line interview summary using LLM.
    
    Args:
        mcq_metadata: Dictionary containing:
            - score (float): MCQ score out of 100
            - time_taken (int/str): Time taken in seconds or formatted string
            - attempted (dict): {"easy": int, "medium": int, "hard": int}
            - correct (dict): {"easy": int, "medium": int, "hard": int}
        
        coding_metadata: Dictionary containing:
            - total_score (float): Coding score out of 100
            - time_taken (int/str): Time taken
            - total_submitted (int): Total questions submitted
            - total_correct (int): Total correct questions
            - partially_correct (int): Partially correct questions
        
        system_design_metadata: Dictionary containing:
            - summary (str): System design summary text
            - score (float): Score out of 100
            - areas_of_improvement (str/list): Areas of improvement
            - key_strengths (str/list): Key strengths
            - time_taken (int/str): Time taken
        
        integrity_metadata: Dictionary containing:
            - tab_switch_count (int): Number of tab switches
            - fullscreen_exits_count (int): Number of fullscreen exits
            - multiple_faces (bool/str): Whether multiple faces detected ("yes"/"no" or boolean)
    
    Returns:
        str: A 4-line summary of the interview performance
    
    Raises:
        ValueError: If LLM provider cannot be initialized
        RuntimeError: If LLM call fails
    """
    try:
        # Initialize LLM provider
        llm = LLMProviderFactory.create_provider()
        
        # Build the prompt
        prompt = _build_summary_prompt(
            mcq_metadata,
            coding_metadata,
            system_design_metadata,
            integrity_metadata
        )
        
        # Create messages
        messages = [
            LLMMessage(
                role="system",
                content="You are an expert interview analyst. Generate concise, professional interview summaries. Always provide exactly 4 lines of summary covering all sections comprehensively."
            ),
            LLMMessage(role="user", content=prompt)
        ]
        
        # Call LLM
        response = await llm.chat_completion(
            messages=messages,
            temperature=0.4,  # Balanced temperature for consistent but natural output
            max_tokens=600  # Enough for 4 lines with some buffer
        )
        
        summary = response.content.strip()
        
        # Ensure we have a proper 4-line summary
        lines = [line.strip() for line in summary.split('\n') if line.strip()]
        
        # If LLM returned more or less than 4 lines, take first 4 or pad
        if len(lines) > 4:
            summary = '\n'.join(lines[:4])
        elif len(lines) < 4:
            # If less than 4 lines, return as is (LLM might have combined lines)
            summary = '\n'.join(lines)
        else:
            summary = '\n'.join(lines)
        
        logger.info("Interview summary generated successfully")
        return summary
        
    except ValueError as e:
        logger.error(f"Failed to initialize LLM provider: {e}")
        raise ValueError(f"LLM provider initialization failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating interview summary: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate interview summary: {str(e)}")


def _build_summary_prompt(
    mcq_metadata: Dict[str, Any],
    coding_metadata: Dict[str, Any],
    system_design_metadata: Dict[str, Any],
    integrity_metadata: Dict[str, Any]
) -> str:
    """
    Build a structured prompt from all metadata.
    
    Args:
        mcq_metadata: MCQ section metadata
        coding_metadata: Coding section metadata
        system_design_metadata: System design section metadata
        integrity_metadata: Integrity metrics metadata
    
    Returns:
        str: Formatted prompt string
    """
    # Format MCQ section
    mcq_score = mcq_metadata.get("score", 0)
    mcq_time = mcq_metadata.get("time_taken", "N/A")
    mcq_attempted = mcq_metadata.get("attempted", {})
    mcq_correct = mcq_metadata.get("correct", {})
    
    mcq_section = f"""MCQ Section:
- Score: {mcq_score}/100
- Time Taken: {mcq_time}
- Attempted: Easy={mcq_attempted.get('easy', 0)}, Medium={mcq_attempted.get('medium', 0)}, Hard={mcq_attempted.get('hard', 0)}
- Correct: Easy={mcq_correct.get('easy', 0)}, Medium={mcq_correct.get('medium', 0)}, Hard={mcq_correct.get('hard', 0)}"""
    
    # Format Coding section
    coding_score = coding_metadata.get("total_score", 0)
    coding_time = coding_metadata.get("time_taken", "N/A")
    coding_submitted = coding_metadata.get("total_submitted", 0)
    coding_correct = coding_metadata.get("total_correct", 0)
    coding_partial = coding_metadata.get("partially_correct", 0)
    
    coding_section = f"""Coding Section:
- Total Score: {coding_score}/100
- Time Taken: {coding_time}
- Questions Submitted: {coding_submitted}
- Fully Correct: {coding_correct}
- Partially Correct: {coding_partial}"""
    
    # Format System Design section
    sd_summary = system_design_metadata.get("summary", "N/A")
    sd_score = system_design_metadata.get("score", 0)
    sd_improvements = system_design_metadata.get("areas_of_improvement", "N/A")
    sd_strengths = system_design_metadata.get("key_strengths", "N/A")
    sd_time = system_design_metadata.get("time_taken", "N/A")
    
    # Handle list or string for improvements and strengths
    if isinstance(sd_improvements, list):
        sd_improvements = ", ".join(str(x) for x in sd_improvements)
    if isinstance(sd_strengths, list):
        sd_strengths = ", ".join(str(x) for x in sd_strengths)
    
    system_design_section = f"""System Design Section:
- Score: {sd_score}/100
- Time Taken: {sd_time}
- Summary: {sd_summary}
- Key Strengths: {sd_strengths}
- Areas of Improvement: {sd_improvements}"""
    
    # Format Integrity section
    tab_switches = integrity_metadata.get("tab_switch_count", 0)
    fullscreen_exits = integrity_metadata.get("fullscreen_exits_count", 0)
    multiple_faces = integrity_metadata.get("multiple_faces", False)
    
    # Convert multiple_faces to readable format
    if isinstance(multiple_faces, bool):
        multiple_faces_str = "Yes" if multiple_faces else "No"
    else:
        multiple_faces_str = str(multiple_faces)
    
    integrity_section = f"""Integrity Metrics:
- Tab Switches: {tab_switches}
- Fullscreen Exits: {fullscreen_exits}
- Multiple Faces Detected: {multiple_faces_str}"""
    
    # Build complete prompt
    prompt = f"""Generate a comprehensive 4-line interview summary based on the following performance data.

{mcq_section}

{coding_section}

{system_design_section}

{integrity_section}

INSTRUCTIONS:
- Provide exactly 4 lines of summary
- Line 1: Overall performance assessment covering MCQ and Coding sections
- Line 2: System Design performance and key observations
- Line 3: Performance breakdown by difficulty levels and problem-solving approach
- Line 4: Integrity assessment and final recommendation
- Be concise, professional, and data-driven
- If integrity concerns exist (high tab switches, fullscreen exits, or multiple faces), mention them appropriately
- Highlight both strengths and areas for improvement
- Use specific numbers and metrics from the data provided

Generate the 4-line summary now:"""
    
    return prompt

