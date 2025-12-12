#!/usr/bin/env python3
"""
Manually Trigger Interview Analysis Generation

This script manually triggers the generation of interview analysis for a candidate
if it's missing or incomplete.

Usage:
    python trigger_analysis.py <candidate_id>
    
Example:
    python trigger_analysis.py d3243f5f-dd2e-4a65-9668-4675b9ad5731
"""

import sys
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def trigger_analysis(candidate_id: str):
    """Trigger analysis generation for a candidate"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Add SSL requirement for Azure PostgreSQL if not present
    if 'sslmode=' not in database_url:
        if '?' in database_url:
            database_url += '&sslmode=require'
        else:
            database_url += '?sslmode=require'
    
    # Create database engine and session
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print(f"🔄 Triggering analysis generation for candidate: {candidate_id}")
        print("-" * 60)
        
        # Import services
        from services.interview_service import InterviewService
        
        # Create service instance
        interview_service = InterviewService(db)
        
        # Trigger ensure_all_analyses_complete
        result = interview_service.ensure_all_analyses_complete(candidate_id)
        
        print(f"✅ Analysis generation completed!")
        print(f"   Success: {result['success']}")
        print(f"   Completed: {result.get('completed_analyses', [])}")
        print(f"   Skipped: {result.get('skipped_analyses', [])}")
        print(f"   Failed: {result.get('failed_analyses', [])}")
        
        if result['success']:
            # Try to generate summary
            print("\n📝 Generating interview summary...")
            try:
                asyncio.run(interview_service.generate_and_save_interview_summary(candidate_id))
                print("✅ Interview summary generated successfully")
            except Exception as e:
                print(f"⚠️  Warning: Could not generate summary: {e}")
            
            # Check if email should be sent
            print("\n📧 Checking email status...")
            from services.email_service import EmailService
            email_service = EmailService()
            
            # Get candidate info
            from models.candidate import Candidate
            candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            
            if candidate:
                are_ready = email_service._are_all_analyses_ready(candidate_id, db)
                print(f"   All analyses ready: {are_ready}")
                
                if are_ready:
                    print("   ✅ Email can be sent (all analyses complete)")
                else:
                    print("   ⏳ Email will be sent when all analyses are ready")
            else:
                print(f"   ⚠️  Candidate not found")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
        engine.dispose()


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python trigger_analysis.py <candidate_id>")
        print()
        print("Example:")
        print("  python trigger_analysis.py d3243f5f-dd2e-4a65-9668-4675b9ad5731")
        sys.exit(1)
    
    candidate_id = sys.argv[1]
    
    # Validate UUID format
    if len(candidate_id) != 36 or candidate_id.count('-') != 4:
        print(f"❌ ERROR: Invalid candidate_id format: {candidate_id}")
        print("Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)
    
    # Trigger analysis
    success = trigger_analysis(candidate_id)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

