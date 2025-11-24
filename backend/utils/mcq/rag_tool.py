"""
RAG Tool for LLM Function Calling
Defines the RAG search function that LLM can call as a tool
"""
from typing import List, Dict, Any, Optional
from services.mcq_rag_service import rag_system


def get_rag_tool_definition() -> Dict[str, Any]:
    """
    Get the RAG search tool definition for Groq function calling
    
    Returns:
        Tool definition dictionary compatible with Groq API
    """
    return {
        "type": "function",
        "function": {
            "name": "search_question_database",
            "description": """Search the question database to find similar example questions based on:
- Query text (keywords, topics, or concepts)
- Difficulty level (easy, medium, or hard)
- Domain (genAI, java_backend, python_backend, java, cloud)

Use this tool when you need inspiration or examples for generating questions. 
You can call this tool multiple times with different queries to explore different subtopics.
The tool returns example questions that you should use as inspiration (NOT to duplicate exactly).""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Search query - can be keywords, topics, technologies, or concepts related to the questions you want to generate. Examples: 'Spring Boot microservices', 'Python async programming', 'Transformer architecture', 'Kubernetes deployment'"
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
                        "description": "Number of similar questions to retrieve (default: 10, max: 20)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query_text", "difficulty", "domain"]
            }
        }
    }


def execute_rag_tool_call(
    query_text: str,
    difficulty: str,
    domain: str,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Execute the RAG tool call and return results
    
    Args:
        query_text: Search query
        difficulty: Difficulty level
        domain: Domain name
        top_k: Number of results
        
    Returns:
        Dictionary with tool call results
    """
    try:
        questions = rag_system.retrieve_similar_questions(
            query_text=query_text,
            difficulty=difficulty,
            domain=domain,
            top_k=min(top_k, 20)  # Cap at 20
        )
        
        # Format results for LLM
        formatted_results = []
        for q in questions:
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
        
        return {
            "success": True,
            "count": len(formatted_results),
            "questions": formatted_results,
            "message": f"Found {len(formatted_results)} similar questions"
        }
    except Exception as e:
        return {
            "success": False,
            "count": 0,
            "questions": [],
            "error": str(e),
            "message": f"Error searching database: {str(e)}"
        }

