#!/usr/bin/env python3
"""
Script to increment question IDs from Q720 onwards by 1
This fixes duplicate IDs in questions.json
Processes questions sequentially to ensure unique IDs
"""
import json
import re

def extract_number(qid):
    """Extract number from question ID like Q720 -> 720"""
    match = re.match(r'Q(\d+)', qid)
    return int(match.group(1)) if match else None

def format_qid(number):
    """Format number as question ID like 720 -> Q720"""
    return f"Q{number:03d}"

def main():
    questions_path = "utils/mcq/questions.json"
    
    print(f"Loading questions from {questions_path}...")
    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"Found {len(questions)} questions")
    
    # Find the highest question number before Q720
    max_id_before_720 = 0
    for q in questions:
        qid = q.get("question_id", "")
        num = extract_number(qid)
        if num and num < 720:
            max_id_before_720 = max(max_id_before_720, num)
    
    print(f"Highest ID before Q720: Q{max_id_before_720:03d}")
    
    # Process all questions sequentially
    # For questions with ID >= 720, assign sequential IDs starting from 720
    current_id = 720
    updated_count = 0
    
    for q in questions:
        qid = q.get("question_id", "")
        num = extract_number(qid)
        
        if num and num >= 720:
            new_qid = format_qid(current_id)
            old_qid = qid
            q["question_id"] = new_qid
            updated_count += 1
            if updated_count <= 5:  # Show first 5 updates
                print(f"  {old_qid} -> {new_qid}")
            current_id += 1
    
    print(f"\nUpdated {updated_count} question IDs (Q720 onwards, sequential from Q720)")
    print(f"New highest ID: Q{current_id - 1:03d}")
    
    # Save the updated file
    print(f"\nSaving updated questions to {questions_path}...")
    with open(questions_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    print("✓ Successfully updated questions.json")
    
    # Verify no duplicates
    all_ids = [q.get("question_id") for q in questions]
    duplicates = [qid for qid in all_ids if all_ids.count(qid) > 1]
    if duplicates:
        print(f"\n⚠ Warning: Found duplicate IDs: {set(duplicates)}")
        return 1
    else:
        print(f"\n✓ Verified: No duplicate IDs found")
        print(f"✓ Total unique questions: {len(set(all_ids))}")
        return 0

if __name__ == "__main__":
    exit(main())
