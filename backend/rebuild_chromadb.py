#!/usr/bin/env python3
"""
Script to rebuild ChromaDB with all questions from questions.json
This will delete the existing collection and recreate it with all 920 questions.
"""
import sys
import os

# Add the backend directory to the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.mcq_rag_service import rag_system
import json

def main():
    """Rebuild ChromaDB vector store with all questions"""
    
    # First, verify the questions file exists and count questions
    questions_path = "utils/mcq/questions.json"
    print(f"Loading questions from {questions_path}...")
    
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        print(f"✓ Found {len(questions)} questions in JSON file")
    except FileNotFoundError:
        print(f"✗ Error: Could not find {questions_path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in {questions_path}: {e}")
        return 1
    
    # Rebuild ChromaDB with force_recreate=True
    print("\n" + "="*60)
    print("Rebuilding ChromaDB vector store...")
    print("This will delete the existing collection and create a new one.")
    print("="*60 + "\n")
    
    try:
        rag_system.initialize_vector_store(force_recreate=True)
        print("\n" + "="*60)
        print("✓ SUCCESS: ChromaDB rebuilt with all questions!")
        print("="*60)
        
        # Verify the count
        if rag_system.collection:
            count = rag_system.collection.count()
            print(f"\n✓ Verified: {count} questions stored in ChromaDB")
        
        return 0
    except Exception as e:
        print(f"\n✗ Error rebuilding ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

