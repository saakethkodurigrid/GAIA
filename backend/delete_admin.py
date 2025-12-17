"""
Script to delete an admin/recruiter from the RECRUITER_ADMIN table.

Usage:
    python delete_admin.py

The script will prompt you to enter the email ID of the admin/recruiter to delete.
"""
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.recruiter_admin import RecruiterAdmin
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def delete_admin(email_id: str) -> bool:
    """
    Delete an admin/recruiter from the database by email_id.
    
    Args:
        email_id: The email ID of the admin/recruiter to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    # Create database engine and session
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin exists
        admin = db.query(RecruiterAdmin).filter(
            RecruiterAdmin.email_id == email_id.lower()
        ).first()
        
        if not admin:
            logger.error(f"Admin/Recruiter with email '{email_id}' not found in database")
            return False
        
        # Display admin details before deletion
        role_name = "Admin" if admin.role_id == 2 else "Recruiter"
        logger.info(f"Found {role_name}:")
        logger.info(f"  Email: {admin.email_id}")
        logger.info(f"  Name: {admin.name}")
        logger.info(f"  Role ID: {admin.role_id}")
        logger.info(f"  Phone: {admin.phone_number or 'N/A'}")
        logger.info(f"  Location: {admin.location or 'N/A'}")
        
        # Delete the admin
        db.delete(admin)
        db.commit()
        
        logger.info(f"✓ Successfully deleted {role_name} with email '{email_id}'")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting admin: {str(e)}", exc_info=True)
        return False
        
    finally:
        db.close()


def main():
    """Main function to handle interactive execution."""
    print("=" * 60)
    print("Admin/Recruiter Deletion Script")
    print("=" * 60)
    
    # Get email as interactive input
    email_id = input("\nEnter the email ID of the admin/recruiter to delete: ").strip()
    
    if not email_id:
        logger.error("Email ID cannot be empty")
        sys.exit(1)
    
    # Validate email format (basic check)
    if '@' not in email_id or '.' not in email_id:
        logger.error("Invalid email format. Please provide a valid email address.")
        sys.exit(1)
    
    # Perform deletion
    success = delete_admin(email_id)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

