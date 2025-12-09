"""
Candidate service for managing candidates.
"""
import uuid
import zlib
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.candidate import Candidate


class CandidateService:
    """Candidate service class for managing candidates."""
    
    def __init__(self, db: Session):
        """Initialize candidate service with database session."""
        self.db = db
    
    def _generate_candidate_reference_number(self, uuid_str: str) -> str:
        """
        Generate a unique 6-digit candidate reference number from UUID.
        Format: CI-XXXXXX (e.g., CI-627891)
        
        Args:
            uuid_str: UUID string to generate reference number from
            
        Returns:
            Formatted candidate reference number string
        """
        # Use CRC32 hash of UUID to get a number
        hash_value = zlib.crc32(uuid_str.encode())
        # Get 6-digit number (000000-999999)
        display_id = abs(hash_value) % 1000000
        
        # Format as "CI-627891"
        formatted_id = f"CI-{display_id:06d}"
        
        # Check for collision
        existing = self.db.query(Candidate).filter(Candidate.candidate_reference_number == formatted_id).first()
        
        if existing:
            # Collision handling: try with a counter until unique
            counter = 1
            while existing:
                new_hash = zlib.crc32((uuid_str + str(counter)).encode())
                display_id = abs(new_hash) % 1000000
                formatted_id = f"CI-{display_id:06d}"
                existing = self.db.query(Candidate).filter(Candidate.candidate_reference_number == formatted_id).first()
                counter += 1
                
                # Safety check to prevent infinite loop (should never happen in practice)
                if counter > 1000:
                    raise Exception("Unable to generate unique candidate reference number after 1000 attempts")
        
        return formatted_id
    
    def get_candidate_by_reference_number(self, candidate_reference_number: str) -> Candidate:
        """
        Get candidate by candidate_reference_number (e.g., "CI-627891").
        Always fetches from database - no conversion/derivation logic.
        Works even if candidate_reference_number is manually updated in database.
        
        Args:
            candidate_reference_number: Candidate reference number to look up
            
        Returns:
            Candidate object if found
            
        Raises:
            ValueError: If candidate with reference number not found
        """
        candidate = self.db.query(Candidate).filter(Candidate.candidate_reference_number == candidate_reference_number).first()
        if not candidate:
            raise ValueError(f"Candidate with reference number {candidate_reference_number} not found")
        return candidate
    
    def get_candidate_uuid_from_reference_number(self, candidate_reference_number: str) -> str:
        """
        Get UUID from candidate_reference_number (legacy method for backward compatibility).
        Uses get_candidate_by_reference_number internally.
        
        Args:
            candidate_reference_number: Candidate reference number to look up
            
        Returns:
            UUID string if found
            
        Raises:
            ValueError: If candidate with reference number not found
        """
        candidate = self.get_candidate_by_reference_number(candidate_reference_number)
        return candidate.candidate_id

