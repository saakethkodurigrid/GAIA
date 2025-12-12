#!/usr/bin/env python3
"""
Reset Test Session for a Candidate

This script resets a candidate's test session to allow them to retake the test.
It clears all previous answers and resets the status to 'in progress'.

Usage:
    python reset_test_session.py <candidate_id>
    
Example:
    python reset_test_session.py d3243f5f-dd2e-4a65-9668-4675b9ad5731
"""

import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_test_session(candidate_id: str):
    """Reset test session for a candidate"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("Please set DATABASE_URL in your .env file or environment")
        sys.exit(1)
    
    # Add SSL requirement for Azure PostgreSQL if not present
    if 'sslmode=' not in database_url:
        if '?' in database_url:
            database_url += '&sslmode=require'
        else:
            database_url += '?sslmode=require'
    
    # Create database engine
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print(f"🔄 Resetting test session for candidate: {candidate_id}")
                print("-" * 60)
                
                # 1. Reset candidate status
                result = conn.execute(
                    text("""
                        UPDATE candidate 
                        SET status = 'in progress'
                        WHERE candidate_id = :candidate_id
                        RETURNING candidate_id, name, email_id, status
                    """),
                    {"candidate_id": candidate_id}
                )
                candidate = result.fetchone()
                
                if not candidate:
                    print(f"❌ ERROR: Candidate {candidate_id} not found")
                    trans.rollback()
                    return False
                
                print(f"✅ Step 1: Reset candidate status to 'in progress'")
                print(f"   Name: {candidate[1]}, Email: {candidate[2]}")
                
                # 2. Reset test session
                conn.execute(
                    text("""
                        UPDATE test_session
                        SET last_heartbeat = NULL,
                            last_activity = NULL,
                            completion_method = NULL,
                            test_completed_at = NULL,
                            sections_completed = '{"mcq": false, "coding": false, "system_design": false}'::jsonb
                        WHERE candidate_id = :candidate_id
                    """),
                    {"candidate_id": candidate_id}
                )
                print(f"✅ Step 2: Reset test session")
                
                # 3. Clear MCQ answers
                result = conn.execute(
                    text("""
                        DELETE FROM interview_mcq 
                        WHERE candidate_id = :candidate_id
                    """),
                    {"candidate_id": candidate_id}
                )
                print(f"✅ Step 3: Deleted {result.rowcount} MCQ answers")
                
                # 4. Clear coding answers
                result = conn.execute(
                    text("""
                        DELETE FROM interview_coding
                        WHERE candidate_id = :candidate_id
                    """),
                    {"candidate_id": candidate_id}
                )
                print(f"✅ Step 4: Deleted {result.rowcount} coding answers")
                
                # 5. Clear system design data
                result = conn.execute(
                    text("""
                        DELETE FROM interview_system_design
                        WHERE candidate_id = :candidate_id
                    """),
                    {"candidate_id": candidate_id}
                )
                print(f"✅ Step 5: Deleted {result.rowcount} system design submissions")
                
                # Commit transaction
                trans.commit()
                
                print("-" * 60)
                print("✨ SUCCESS! Test session has been reset")
                print()
                print("📝 Next steps:")
                print("1. Clear browser localStorage (run in console):")
                print("   localStorage.clear(); location.reload();")
                print()
                print("2. (Optional) Clear Redis cache:")
                print(f"   redis-cli DEL test:{candidate_id}:*")
                print()
                print("3. Candidate can now retake the test")
                
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ ERROR during reset: {str(e)}")
                return False
                
    except Exception as e:
        print(f"❌ ERROR connecting to database: {str(e)}")
        return False
    finally:
        engine.dispose()


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python reset_test_session.py <candidate_id>")
        print()
        print("Example:")
        print("  python reset_test_session.py d3243f5f-dd2e-4a65-9668-4675b9ad5731")
        sys.exit(1)
    
    candidate_id = sys.argv[1]
    
    # Validate UUID format
    if len(candidate_id) != 36 or candidate_id.count('-') != 4:
        print(f"❌ ERROR: Invalid candidate_id format: {candidate_id}")
        print("Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)
    
    # Confirm with user
    print()
    print("⚠️  WARNING: This will delete all test data for this candidate!")
    print(f"Candidate ID: {candidate_id}")
    print()
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Operation cancelled")
        sys.exit(0)
    
    # Reset test session
    success = reset_test_session(candidate_id)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

