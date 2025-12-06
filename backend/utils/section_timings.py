"""
Utility functions for tracking section timings during tests.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from models.candidate import Candidate


def start_section_timing(candidate: Candidate, section_name: str) -> None:
    """
    Record when a candidate starts a section.
    
    Args:
        candidate: Candidate model instance
        section_name: Name of the section (e.g., 'mcq', 'coding', 'system_design')
    """
    if not candidate.test_session:
        return
        
    section_timings = candidate.test_session.section_timings or {}
    section_timings[section_name] = {
        'started_at': datetime.utcnow().isoformat()
    }
    candidate.test_session.section_timings = section_timings


def complete_section_timing(candidate: Candidate, section_name: str) -> Optional[int]:
    """
    Record when a candidate completes a section and calculate duration.
    
    Args:
        candidate: Candidate model instance
        section_name: Name of the section (e.g., 'mcq', 'coding', 'system_design')
    
    Returns:
        Duration in seconds, or None if section wasn't started
    """
    if not candidate.test_session:
        return None
        
    section_timings = candidate.test_session.section_timings or {}
    
    if section_name not in section_timings or 'started_at' not in section_timings[section_name]:
        return None
    
    started_at_str = section_timings[section_name]['started_at']
    started_at = datetime.fromisoformat(started_at_str)
    completed_at = datetime.utcnow()
    duration_seconds = int((completed_at - started_at).total_seconds())
    
    section_timings[section_name].update({
        'completed_at': completed_at.isoformat(),
        'duration_seconds': duration_seconds
    })
    candidate.test_session.section_timings = section_timings
    
    return duration_seconds


def get_section_timing(candidate: Candidate, section_name: str) -> Optional[Dict[str, Any]]:
    """
    Get timing information for a specific section.
    
    Args:
        candidate: Candidate model instance
        section_name: Name of the section
    
    Returns:
        Dictionary with timing info or None if section not found
    """
    if not candidate.test_session:
        return None
        
    section_timings = candidate.test_session.section_timings or {}
    return section_timings.get(section_name)

