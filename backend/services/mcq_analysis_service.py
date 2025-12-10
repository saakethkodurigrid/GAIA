"""
MCQ Analysis Service for generating assessment summaries.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.interview_analysis_table import InterviewAnalysisTable
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage

logger = logging.getLogger(__name__)


async def generate_mcq_analysis(candidate_id: str, db: Session) -> Dict[str, Any]:
    """
    Generate MCQ analysis summary, strengths, and areas for improvement using LLM.
    Fetches data from InterviewAnalysisTable.mcq_analysis.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
        
    Returns:
        Dictionary with:
            - summary: Brief overview of MCQ performance
            - strengths: List of 2-3 key strengths
            - improvements: List of 2-3 areas for improvement
    """
    try:
        # Fetch MCQ analysis from InterviewAnalysisTable
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if not interview_analysis or not interview_analysis.mcq_analysis:
            return {
                "summary": "No MCQ questions were attempted.",
                "strengths": [],
                "improvements": []
            }
        
        # Extract performance data from mcq_analysis JSONB
        mcq_data = interview_analysis.mcq_analysis
        
        # Extract metrics from the analysis data
        # Handle different possible structures
        total_questions = mcq_data.get("total_questions", 0)
        attempted_questions = mcq_data.get("attempted_questions", mcq_data.get("attempted", 0))
        correct_answers = mcq_data.get("correct_answers", mcq_data.get("correct", 0))
        total_score = mcq_data.get("total_score", mcq_data.get("score", 0))
        accuracy = mcq_data.get("accuracy", 0)
        
        # If accuracy not provided, calculate it
        if accuracy == 0 and attempted_questions > 0:
            accuracy = (correct_answers / attempted_questions * 100)
        
        # Extract difficulty breakdown
        difficulty_stats = mcq_data.get("difficulty_stats", mcq_data.get("difficulty_breakdown", {}))
        if not difficulty_stats:
            difficulty_stats = {"easy": {"attempted": 0, "correct": 0}, 
                              "medium": {"attempted": 0, "correct": 0},
                              "hard": {"attempted": 0, "correct": 0}}
        
        # Extract topic breakdown
        topic_stats = mcq_data.get("topic_stats", mcq_data.get("topic_breakdown", {}))
        
        # Build prompt for LLM
        prompt = _build_mcq_analysis_prompt(
            total_questions=total_questions,
            attempted_questions=attempted_questions,
            correct_answers=correct_answers,
            total_score=total_score,
            accuracy=accuracy,
            difficulty_stats=difficulty_stats,
            topic_stats=topic_stats
        )
        
        # Initialize LLM provider
        llm = LLMProviderFactory.create_provider()
        
        # Create messages
        messages = [
            LLMMessage(
                role="system",
                content="You are an expert interview analyst. Generate concise, professional MCQ assessment summaries. Always provide exactly: 1) a brief summary (2-3 sentences), 2) 2-3 key strengths, and 3) 2-3 areas for improvement. Format your response as JSON with keys: 'summary', 'strengths' (array), and 'improvements' (array)."
            ),
            LLMMessage(role="user", content=prompt)
        ]
        
        # Call LLM
        response = await llm.chat_completion(
            messages=messages,
            temperature=0.4,
            max_tokens=500
        )
        
        # Parse LLM response
        analysis = _parse_llm_response(response.content)
        
        # Fallback if parsing fails
        if not analysis:
            analysis = {
                "summary": f"Completed {attempted_questions} out of {total_questions} questions with {correct_answers} correct answers ({accuracy:.1f}% accuracy).",
                "strengths": ["Demonstrated knowledge across multiple topics"] if correct_answers > 0 else [],
                "improvements": ["Focus on improving accuracy in challenging topics"] if accuracy < 80 else []
            }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error generating MCQ analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
        # Return fallback analysis
        return {
            "summary": "MCQ assessment completed. Analysis generation encountered an issue.",
            "strengths": [],
            "improvements": []
        }


def _build_mcq_analysis_prompt(
    total_questions: int,
    attempted_questions: int,
    correct_answers: int,
    total_score: int,
    accuracy: float,
    difficulty_stats: Dict[str, Dict[str, int]],
    topic_stats: Dict[str, Dict[str, int]]
) -> str:
    """Build structured prompt for MCQ analysis."""
    
    # Format difficulty breakdown
    difficulty_text = "\n".join([
        f"- {diff.capitalize()}: {stats['attempted']} attempted, {stats['correct']} correct"
        for diff, stats in difficulty_stats.items()
        if stats['attempted'] > 0
    ])
    
    # Format top topics (top 5)
    topic_text = ""
    if topic_stats:
        sorted_topics = sorted(
            topic_stats.items(),
            key=lambda x: x[1]['attempted'],
            reverse=True
        )[:5]
        topic_text = "\n".join([
            f"- {topic}: {stats['attempted']} attempted, {stats['correct']} correct"
            for topic, stats in sorted_topics
        ])
    
    prompt = f"""Analyze the following MCQ assessment performance and provide feedback:

PERFORMANCE METRICS:
- Total Questions: {total_questions}
- Attempted: {attempted_questions}
- Correct Answers: {correct_answers}
- Total Score: {total_score}
- Accuracy: {accuracy:.1f}%

DIFFICULTY BREAKDOWN:
{difficulty_text if difficulty_text else "- No difficulty data available"}

TOPIC BREAKDOWN:
{topic_text if topic_text else "- No topic data available"}

INSTRUCTIONS:
Generate a JSON response with exactly these keys:
1. "summary": A brief 2-3 sentence overview of overall MCQ performance
2. "strengths": An array of 2-3 specific strengths (e.g., "Strong understanding of data structures", "Good grasp of fundamental concepts")
3. "improvements": An array of 2-3 specific areas for improvement (e.g., "Review advanced algorithm optimization techniques", "Deepen knowledge in distributed systems concepts")

Be specific and constructive. Focus on actionable feedback.

Response format (JSON only, no markdown):
{{
  "summary": "...",
  "strengths": ["...", "..."],
  "improvements": ["...", "..."]
}}"""
    
    return prompt


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM response and extract structured analysis."""
    import json
    import re
    
    try:
        # Try to extract JSON from response
        # Remove markdown code blocks if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        response_text = response_text.strip()
        
        # Try to find JSON object
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            
            # Validate structure
            if isinstance(parsed, dict):
                result = {
                    "summary": parsed.get("summary", ""),
                    "strengths": parsed.get("strengths", []),
                    "improvements": parsed.get("improvements", [])
                }
                
                # Ensure lists are lists
                if not isinstance(result["strengths"], list):
                    result["strengths"] = []
                if not isinstance(result["improvements"], list):
                    result["improvements"] = []
                
                return result
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {str(e)}")
    
    # Fallback: try to extract from text
    try:
        lines = response_text.split('\n')
        summary = ""
        strengths = []
        improvements = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'summary' in line.lower() or 'overall' in line.lower():
                current_section = 'summary'
                summary = line.split(':', 1)[-1].strip() if ':' in line else line
            elif 'strength' in line.lower():
                current_section = 'strengths'
            elif 'improvement' in line.lower() or 'area' in line.lower():
                current_section = 'improvements'
            elif line.startswith('-') or line.startswith('•'):
                item = line[1:].strip()
                if current_section == 'strengths':
                    strengths.append(item)
                elif current_section == 'improvements':
                    improvements.append(item)
            elif current_section == 'summary' and not summary:
                summary = line
        
        if summary or strengths or improvements:
            return {
                "summary": summary or "MCQ assessment completed.",
                "strengths": strengths[:3],
                "improvements": improvements[:3]
            }
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as text: {str(e)}")
    
    return None

