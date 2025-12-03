"""
RAG Tool for LLM Function Calling
Defines the RAG search function that LLM can call as a tool
"""
from typing import List, Dict, Any, Optional
from services.mcq_rag_service import rag_system
from llm.models import ToolDefinition


def get_rag_tool_definition() -> ToolDefinition:
    """
    Get the RAG search tool definition in STANDARDIZED format
    
    Returns:
        ToolDefinition in platform-agnostic format
    """
    return ToolDefinition(
        name="search_question_database",
        description="""Search the question database to find similar example questions based on:
- Query text (keywords, topics, or concepts) OR a list of subtopics
- Difficulty level (easy, medium, or hard)
- Domain (genAI, java_backend, python_backend, java, cloud)

Use this tool ONCE to get all relevant examples for all subtopics. 
You can provide either:
- A single query_text (for general search)
- A list of subtopics (to search all subtopics at once - RECOMMENDED)

The tool returns example questions that you should use as inspiration (NOT to duplicate exactly).""",
        parameters={
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "Search query - keywords, topics, technologies, or concepts. Use this OR subtopics (not both)."
                },
                "subtopics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of subtopics to search for. The tool will search all subtopics and return combined, deduplicated results. Use this OR query_text (not both). RECOMMENDED: Pass all subtopics at once."
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Difficulty level of questions to search for. Must match the difficulty you're currently generating."
                },
                "domain": {
                    "type": "string",
                    "enum": ["genAI", "java_backend", "python_backend", "java", "cloud"],
                    "description": "Domain/category of questions. Must match the domain you're working with."
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of similar questions to retrieve per subtopic/query (default: 10, max: 20). If subtopics provided, total results may be up to top_k * number_of_subtopics (deduplicated).",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20
                }
            },
            "required": ["difficulty", "domain"]
        }
    )


def execute_rag_tool_call(
    query_text: Optional[str] = None,
    subtopics: Optional[List[str]] = None,
    difficulty: str = None,
    domain: str = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Execute the RAG tool call and return results
    
    Args:
        query_text: Search query (optional if subtopics provided)
        subtopics: List of subtopics to search (optional if query_text provided)
        difficulty: Difficulty level
        domain: Domain name
        top_k: Number of results per query
        
    Returns:
        Dictionary with tool call results
    """
    try:
        all_questions = []
        seen_question_ids = set()
        
        if subtopics and len(subtopics) > 0:
            # Search each subtopic and combine results
            for subtopic in subtopics:
                questions = rag_system.retrieve_similar_questions(
                    query_text=subtopic,
                    difficulty=difficulty,
                    domain=domain,
                    top_k=top_k
                )
                
                # Deduplicate by question_id
                for q in questions:
                    q_id = q.get("question_id", "")
                    if q_id and q_id not in seen_question_ids:
                        seen_question_ids.add(q_id)
                        all_questions.append(q)
        elif query_text:
            # Single query search
            all_questions = rag_system.retrieve_similar_questions(
                query_text=query_text,
                difficulty=difficulty,
                domain=domain,
                top_k=top_k
            )
        else:
            # Fallback: use domain + difficulty as query
            all_questions = rag_system.retrieve_similar_questions(
                query_text=f"{domain} {difficulty}",
                difficulty=difficulty,
                domain=domain,
                top_k=top_k
            )
        
        # Format results for LLM
        formatted_results = []
        for q in all_questions[:50]:  # Cap total results at 50
            formatted_results.append({
                "question_id": q.get("question_id", ""),
                "question": q.get("question", ""),
                "options": [
                    q.get("option1", ""),
                    q.get("option2", ""),
                    q.get("option3", ""),
                    q.get("option4", "")
                ],
                "correct_option": q.get("correct_option", 1),
                "difficulty": q.get("difficulty", ""),
                "tags": q.get("tags", [])
            })
        
        search_count = len(subtopics) if subtopics and len(subtopics) > 0 else 1
        return {
            "success": True,
            "count": len(formatted_results),
            "questions": formatted_results,
            "message": f"Found {len(formatted_results)} similar questions across {search_count} search{'es' if search_count > 1 else ''}"
        }
    except Exception as e:
        return {
            "success": False,
            "count": 0,
            "questions": [],
            "error": str(e),
            "message": f"Error searching database: {str(e)}"
        }

