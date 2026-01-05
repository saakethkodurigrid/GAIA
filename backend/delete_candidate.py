"""
Script to delete a candidate and all related data from the database.

This script deletes a candidate_id and all related records from:
- TestSession (if table exists)
- InterviewMCQ
- InterviewCoding
- InterviewSystemDesign
- InterviewAnalysisTable
- RecruiterAdminCandidate
- AnalysisStatus
- Candidate

Note: Test session data is now stored in a separate test_session table.
The test_session record will be automatically deleted when the Candidate record
is deleted (due to CASCADE), but we delete it explicitly for clarity.

Usage:
    python delete_candidate.py <candidate_id>
    or
    python delete_candidate.py  # Will prompt for candidate_id
"""
import sys
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, OperationalError
from core.database import SessionLocal
from models.candidate import Candidate
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.interview_system_design import InterviewSystemDesign
from models.interview_analysis_table import InterviewAnalysisTable
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.analysis_status import AnalysisStatusRecord

# Try to import TestSession, but handle if table doesn't exist
try:
    from models.test_session import TestSession
    TEST_SESSION_AVAILABLE = True
except Exception:
    TEST_SESSION_AVAILABLE = False
    TestSession = None


def delete_candidate_and_related_data(db: Session, candidate_id: str) -> dict:
    """
    Delete a candidate and all related data from the database.
    
    Args:
        db: Database session
        candidate_id: The candidate ID to delete
        
    Returns:
        dict: Summary of deleted records
    """
    # Check if candidate exists using raw SQL to avoid test_session relationship issues
    from sqlalchemy import text
    result = db.execute(
        text("SELECT candidate_id FROM candidate WHERE candidate_id = :candidate_id"),
        {"candidate_id": candidate_id}
    ).fetchone()
    
    if not result:
        return {
            'success': False,
            'message': f'Candidate with ID {candidate_id} not found.',
            'deleted_counts': {}
        }
    
    # Try to get candidate object, but handle if test_session table doesn't exist
    candidate = None
    try:
        from sqlalchemy.orm import noload
        candidate = db.query(Candidate).options(noload(Candidate.test_session)).filter(
            Candidate.candidate_id == candidate_id
        ).first()
    except (ProgrammingError, OperationalError) as e:
        # test_session table doesn't exist - we'll use raw SQL for deletion
        # Just set candidate to a simple object with the ID
        class SimpleCandidate:
            def __init__(self, candidate_id):
                self.candidate_id = candidate_id
        candidate = SimpleCandidate(candidate_id)
    
    deleted_counts = {}
    
    try:
        # 0. Delete TestSession record if table exists (optional, CASCADE will handle it)
        if TEST_SESSION_AVAILABLE:
            try:
                test_session = db.query(TestSession).filter(
                    TestSession.candidate_id == candidate_id
                ).first()
                deleted_counts['test_session'] = 1 if test_session else 0
                if test_session:
                    db.delete(test_session)
            except (ProgrammingError, OperationalError) as e:
                # Table doesn't exist yet, skip it
                deleted_counts['test_session'] = 0
                pass
        
        # 1. Delete InterviewMCQ records (has foreign key to candidate)
        mcq_records = db.query(InterviewMCQ).filter(
            InterviewMCQ.candidate_id == candidate_id
        ).all()
        deleted_counts['interview_mcq'] = len(mcq_records)
        for mcq in mcq_records:
            db.delete(mcq)
        
        # 2. Delete InterviewCoding records (composite PK with candidate_id)
        coding_records = db.query(InterviewCoding).filter(
            InterviewCoding.candidate_id == candidate_id
        ).all()
        deleted_counts['interview_coding'] = len(coding_records)
        for coding in coding_records:
            db.delete(coding)
        
        # 3. Delete InterviewSystemDesign records (composite PK with candidate_id)
        system_design_records = db.query(InterviewSystemDesign).filter(
            InterviewSystemDesign.candidate_id == candidate_id
        ).all()
        deleted_counts['interview_system_design'] = len(system_design_records)
        for sd in system_design_records:
            db.delete(sd)
        
        # 4. Delete InterviewAnalysisTable record (candidate_id is primary key)
        analysis_record = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        deleted_counts['interview_analysis_table'] = 1 if analysis_record else 0
        if analysis_record:
            db.delete(analysis_record)
        
        # 5. Delete RecruiterAdminCandidate records (composite PK with candidate_id)
        assignment_records = db.query(RecruiterAdminCandidate).filter(
            RecruiterAdminCandidate.candidate_id == candidate_id
        ).all()
        deleted_counts['recruiter_admin_candidate'] = len(assignment_records)
        for assignment in assignment_records:
            db.delete(assignment)
        
        # 6. Delete AnalysisStatusRecord records (foreign key to candidate)
        analysis_status_records = db.query(AnalysisStatusRecord).filter(
            AnalysisStatusRecord.candidate_id == candidate_id
        ).all()
        deleted_counts['analysis_status'] = len(analysis_status_records)
        for status_record in analysis_status_records:
            db.delete(status_record)
        
        # 7. Finally, delete the Candidate record
        # Use raw SQL if candidate is not a proper ORM object (test_session table missing)
        if not hasattr(candidate, '__table__'):
            # It's a simple object, delete by ID using raw SQL
            db.execute(
                text("DELETE FROM candidate WHERE candidate_id = :candidate_id"),
                {"candidate_id": candidate_id}
            )
        else:
            # It's a proper ORM object
            db.delete(candidate)
        deleted_counts['candidate'] = 1
        
        # Commit all deletions
        db.commit()
        
        return {
            'success': True,
            'message': f'Successfully deleted candidate {candidate_id} and all related data.',
            'deleted_counts': deleted_counts
        }
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        return {
            'success': False,
            'message': f'Error deleting candidate: {str(e)}',
            'deleted_counts': deleted_counts
        }


def main():
    """Main function to run the script."""
    # Get candidate_id from command line argument or prompt
    if len(sys.argv) > 1:
        candidate_id = sys.argv[1]
    else:
        candidate_id = input("Enter candidate_id to delete: ").strip()
    
    if not candidate_id:
        print("Error: candidate_id cannot be empty.")
        sys.exit(1)
    
    # Create database session
    db = SessionLocal()
    
    try:
        print(f"\nDeleting candidate {candidate_id} and all related data...")
        print("=" * 60)
        
        result = delete_candidate_and_related_data(db, candidate_id)
        
        if result['success']:
            print(f"\n✓ {result['message']}")
            print("\nDeleted records summary:")
            print("-" * 60)
            for table, count in result['deleted_counts'].items():
                print(f"  {table}: {count} record(s)")
            print("=" * 60)
        else:
            print(f"\n✗ {result['message']}")
            if result['deleted_counts']:
                print("\nPartial deletion summary:")
                print("-" * 60)
                for table, count in result['deleted_counts'].items():
                    print(f"  {table}: {count} record(s)")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        db.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

