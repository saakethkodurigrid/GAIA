"""
Coding Analysis Service for generating assessment summaries.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.interview_analysis_table import InterviewAnalysisTable
from llm.factory import LLMProviderFactory
from llm.models import LLMMessage

logger = logging.getLogger(__name__)


async def generate_coding_analysis(candidate_id: str, db: Session) -> Dict[str, Any]:
    """
    Generate Coding analysis summary, strengths, and areas for improvement using LLM.
    Fetches data from InterviewAnalysisTable.coding_analysis.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
        
    Returns:
        Dictionary with:
            - summary: Brief overview of coding performance
            - strengths: List of 2-3 key strengths
            - improvements: List of 2-3 areas for improvement
    """
    try:
        # Fetch Coding analysis from InterviewAnalysisTable
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if not interview_analysis or not interview_analysis.coding_analysis:
            return {
                "summary": "No coding questions were submitted.",
                "strengths": [],
                "improvements": []
            }
        
        # Extract performance data from coding_analysis JSONB
        coding_data = interview_analysis.coding_analysis
        
        # Extract metrics from the analysis data
        # Handle different possible structures
        total_questions = coding_data.get("total_questions", 0)
        submitted_questions = coding_data.get("submitted_questions", coding_data.get("submitted", 0))
        total_score = coding_data.get("total_score", coding_data.get("score", 0))
        total_test_cases_passed = coding_data.get("total_test_cases_passed", coding_data.get("test_cases_passed", 0))
        total_test_cases = coding_data.get("total_test_cases", 0)
        fully_correct = coding_data.get("fully_correct", coding_data.get("total_correct", 0))
        partially_correct = coding_data.get("partially_correct", 0)
        
        # Calculate metrics if not provided
        avg_score_per_question = coding_data.get("avg_score_per_question", 0)
        if avg_score_per_question == 0 and submitted_questions > 0:
            avg_score_per_question = (total_score / submitted_questions)
        
        test_case_pass_rate = coding_data.get("test_case_pass_rate", coding_data.get("test_case_pass_rate_percent", 0))
        if test_case_pass_rate == 0 and total_test_cases > 0:
            test_case_pass_rate = (total_test_cases_passed / total_test_cases * 100)
        
        # Extract difficulty breakdown
        difficulty_stats = coding_data.get("difficulty_stats", coding_data.get("difficulty_breakdown", {}))
        if not difficulty_stats:
            difficulty_stats = {"easy": {"submitted": 0, "avg_score": 0}, 
                              "medium": {"submitted": 0, "avg_score": 0},
                              "hard": {"submitted": 0, "avg_score": 0}}
        
        # Extract topic breakdown
        topic_stats = coding_data.get("topic_stats", coding_data.get("topic_breakdown", {}))
        
        # Build prompt for LLM
        prompt = _build_coding_analysis_prompt(
            total_questions=total_questions,
            submitted_questions=submitted_questions,
            fully_correct=fully_correct,
            partially_correct=partially_correct,
            total_score=total_score,
            avg_score_per_question=avg_score_per_question,
            total_test_cases_passed=total_test_cases_passed,
            total_test_cases=total_test_cases,
            test_case_pass_rate=test_case_pass_rate,
            difficulty_stats=difficulty_stats,
            topic_stats=topic_stats
        )
        
        # Initialize LLM provider
        llm = LLMProviderFactory.create_provider()
        
        # Create messages
        messages = [
            LLMMessage(
                role="system",
                content="You are an expert coding interview analyst. Generate concise, professional coding assessment summaries. Always provide exactly: 1) a brief summary (1-2 sentences), 2) 2-3 key strengths, and 3) 2-3 areas for improvement. Format your response as JSON with keys: 'summary', 'strengths' (array), and 'improvements' (array)."
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
                "summary": f"Submitted {submitted_questions} out of {total_questions} coding questions with {fully_correct} fully correct solutions ({test_case_pass_rate:.1f}% test case pass rate).",
                "strengths": ["Demonstrated coding problem-solving skills"] if fully_correct > 0 else [],
                "improvements": ["Focus on improving test case coverage"] if test_case_pass_rate < 80 else []
            }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error generating coding analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
        # Return fallback analysis
        return {
            "summary": "Coding assessment completed. Analysis generation encountered an issue.",
            "strengths": [],
            "improvements": []
        }


def _build_coding_analysis_prompt(
    total_questions: int,
    submitted_questions: int,
    fully_correct: int,
    partially_correct: int,
    total_score: int,
    avg_score_per_question: float,
    total_test_cases_passed: int,
    total_test_cases: int,
    test_case_pass_rate: float,
    difficulty_stats: Dict[str, Dict[str, Any]],
    topic_stats: Dict[str, Dict[str, Any]]
) -> str:
    """Build structured prompt for coding analysis."""
    
    # Format difficulty breakdown
    difficulty_text = "\n".join([
        f"- {diff.capitalize()}: {stats['submitted']} submitted, avg score {stats['avg_score']:.1f}"
        for diff, stats in difficulty_stats.items()
        if stats['submitted'] > 0
    ])
    
    # Format top topics (top 5)
    topic_text = ""
    if topic_stats:
        sorted_topics = sorted(
            topic_stats.items(),
            key=lambda x: x[1]['submitted'],
            reverse=True
        )[:5]
        topic_text = "\n".join([
            f"- {topic}: {stats['submitted']} submitted, avg score {stats['total_score']/stats['submitted']:.1f if stats['submitted'] > 0 else 0:.1f}"
            for topic, stats in sorted_topics
        ])
    
    prompt = f"""Analyze the following coding assessment performance and provide feedback:

PERFORMANCE METRICS:
- Total Questions: {total_questions}
- Submitted: {submitted_questions}
- Fully Correct: {fully_correct}
- Partially Correct: {partially_correct}
- Total Score: {total_score}
- Average Score per Question: {avg_score_per_question:.1f}
- Test Cases Passed: {total_test_cases_passed} / {total_test_cases}
- Test Case Pass Rate: {test_case_pass_rate:.1f}%

DIFFICULTY BREAKDOWN:
{difficulty_text if difficulty_text else "- No difficulty data available"}

TOPIC BREAKDOWN:
{topic_text if topic_text else "- No topic data available"}

INSTRUCTIONS:
Generate a JSON response with exactly these keys:
1. "summary": A brief 1-2 sentence overview of overall coding performance
2. "strengths": An array of 2-3 specific strengths (e.g., "Good consideration of scalability and load balancing", "Appropriate use of caching strategy")
3. "improvements": An array of 2-3 specific areas for improvement (e.g., "Discuss fault tolerance and disaster recovery plans", "Consider CDN integration for better global performance")

Be specific and constructive. Focus on software engineering best practices, problem-solving approach, and code quality.

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
                "summary": summary or "Coding assessment completed.",
                "strengths": strengths[:3],
                "improvements": improvements[:3]
            }
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as text: {str(e)}")
    
    return None

