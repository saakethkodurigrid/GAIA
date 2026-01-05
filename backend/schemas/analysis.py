"""
Analysis status schemas and enums.
"""
from enum import Enum


class AnalysisStatus(str, Enum):
    """Analysis status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SectionType(str, Enum):
    """Section type enumeration for analysis tracking."""
    MCQ = "MCQ"
    CODING = "CODING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    FINAL = "FINAL"

