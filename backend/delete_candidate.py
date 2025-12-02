"""
Script to delete a candidate and all related data from the database.

This script deletes a candidate_id and all related records from:
- InterviewMCQ
- InterviewCoding
- InterviewSystemDesign
- InterviewAnalysisTable
- RecruiterAdminCandidate
- Candidate

Usage:
    python delete_candidate.py <candidate_id>
    or
    python delete_candidate.py  # Will prompt for candidate_id
"""
import sys
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.candidate import Candidate
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.interview_system_design import InterviewSystemDesign
from models.interview_analysis_table import InterviewAnalysisTable
from models.recruiter_admin_candidate import RecruiterAdminCandidate


def delete_candidate_and_related_data(db: Session, candidate_id: str) -> dict:
    """
    Delete a candidate and all related data from the database.
    
    Args:
        db: Database session
        candidate_id: The candidate ID to delete
        
    Returns:
        dict: Summary of deleted records
    """
    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        return {
            'success': False,
            'message': f'Candidate with ID {candidate_id} not found.',
            'deleted_counts': {}
        }
    
    deleted_counts = {}
    
    try:
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
        
        # 6. Finally, delete the Candidate record
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

