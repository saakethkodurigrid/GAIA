#!/usr/bin/env python3
"""
Script to verify that all questions from questions.json are in ChromaDB
"""
import sys
import os
import json

# Add the backend directory to the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.mcq_rag_service import rag_system

def main():
    """Verify all questions are in ChromaDB"""
    
    print("="*60)
    print("ChromaDB Verification Script")
    print("="*60 + "\n")
    
    # Step 1: Load and count questions from JSON
    questions_path = "utils/mcq/questions.json"
    print(f"1. Loading questions from {questions_path}...")
    
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            json_questions = json.load(f)
        json_count = len(json_questions)
        print(f"   ✓ Found {json_count} questions in JSON file")
    except Exception as e:
        print(f"   ✗ Error loading JSON: {e}")
        return 1
    
    # Get all question IDs from JSON
    json_ids = set()
    for q in json_questions:
        qid = q.get("question_id", "")
        if qid:
            json_ids.add(qid)
    
    print(f"   ✓ Found {len(json_ids)} unique question IDs in JSON\n")
    
    # Step 2: Initialize and count questions in ChromaDB
    print("2. Connecting to ChromaDB...")
    
    try:
        # Initialize the RAG system (won't recreate if it exists)
        rag_system.initialize_vector_store(force_recreate=False)
        print("   ✓ Connected to ChromaDB")
        
        if not rag_system.collection:
            print("   ✗ Error: ChromaDB collection not found")
            return 1
        
        # Get count from ChromaDB
        chroma_count = rag_system.collection.count()
        print(f"   ✓ ChromaDB collection has {chroma_count} questions\n")
        
        # Get all question IDs from ChromaDB
        print("3. Retrieving question IDs from ChromaDB...")
        chroma_results = rag_system.collection.get()
        chroma_ids = set(chroma_results['ids'])
        print(f"   ✓ Found {len(chroma_ids)} unique question IDs in ChromaDB\n")
        
    except Exception as e:
        print(f"   ✗ Error accessing ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 3: Compare
    print("4. Comparing JSON and ChromaDB...")
    print("   " + "-"*56)
    
    # Find missing questions
    missing_in_chroma = json_ids - chroma_ids
    extra_in_chroma = chroma_ids - json_ids
    
    print(f"   JSON questions:        {len(json_ids)}")
    print(f"   ChromaDB questions:     {len(chroma_ids)}")
    print(f"   Missing in ChromaDB:    {len(missing_in_chroma)}")
    print(f"   Extra in ChromaDB:      {len(extra_in_chroma)}")
    print("   " + "-"*56 + "\n")
    
    # Step 4: Report results
    if len(missing_in_chroma) == 0 and len(extra_in_chroma) == 0:
        print("="*60)
        print("✓ SUCCESS: All questions match!")
        print(f"✓ All {json_count} questions from JSON are in ChromaDB")
        print("="*60)
        
        # Show sample of question IDs
        print("\nSample question IDs (first 10):")
        sample_ids = sorted(list(json_ids))[:10]
        for qid in sample_ids:
            print(f"   - {qid}")
        if len(json_ids) > 10:
            print(f"   ... and {len(json_ids) - 10} more")
        
        return 0
    else:
        print("="*60)
        print("⚠ MISMATCH DETECTED")
        print("="*60)
        
        if missing_in_chroma:
            print(f"\nMissing in ChromaDB ({len(missing_in_chroma)} questions):")
            missing_sorted = sorted(list(missing_in_chroma))
            for qid in missing_sorted[:20]:  # Show first 20
                print(f"   - {qid}")
            if len(missing_in_chroma) > 20:
                print(f"   ... and {len(missing_in_chroma) - 20} more")
        
        if extra_in_chroma:
            print(f"\nExtra in ChromaDB ({len(extra_in_chroma)} questions):")
            extra_sorted = sorted(list(extra_in_chroma))
            for qid in extra_sorted[:20]:  # Show first 20
                print(f"   - {qid}")
            if len(extra_in_chroma) > 20:
                print(f"   ... and {len(extra_in_chroma) - 20} more")
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

