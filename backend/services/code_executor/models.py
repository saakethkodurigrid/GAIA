"""
Data models for code execution service
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class Language(str, Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"


class ExecutionStatus(str, Enum):
    """Execution status codes"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    COMPILATION_ERROR = "compilation_error"


@dataclass
class TestCase:
    """Test case for code execution"""
    input: str
    expected_output: str
    test_id: Optional[int] = None
    
    def __post_init__(self):
        # Normalize line endings
        self.expected_output = self.expected_output.strip()


@dataclass
class TestResult:
    """Result of a single test case"""
    test_id: Optional[int]
    input: str
    expected_output: str
    actual_output: str
    passed: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class ExecutionMetrics:
    """Metrics for code execution"""
    total_execution_time_ms: float
    memory_used_mb: float
    cpu_time_ms: float
    container_startup_time_ms: float
    code_execution_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExecutionRequest:
    """Request to execute code"""
    code: str
    language: Language
    test_cases: List[TestCase] = field(default_factory=list)
    timeout: int = 30  # seconds
    memory_limit: int = 256  # MB
    problem_id: Optional[int] = None


@dataclass
class ExecutionResult:
    """Result of code execution"""
    status: ExecutionStatus
    stdout: str
    stderr: str
    test_results: List[TestResult]
    metrics: ExecutionMetrics
    compilation_output: Optional[str] = None
    error_message: Optional[str] = None
    execution_id: Optional[str] = None
    
    @property
    def all_tests_passed(self) -> bool:
        """Check if all test cases passed"""
        if not self.test_results:
            return False
        return all(result.passed for result in self.test_results)
    
    @property
    def tests_passed_count(self) -> int:
        """Count of passed test cases"""
        return sum(1 for result in self.test_results if result.passed)
    
    @property
    def tests_failed_count(self) -> int:
        """Count of failed test cases"""
        return sum(1 for result in self.test_results if not result.passed)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "compilation_output": self.compilation_output,
            "error_message": self.error_message,
            "execution_id": self.execution_id,
            "test_results": [
                {
                    "test_id": tr.test_id,
                    "input": tr.input,
                    "expected_output": tr.expected_output,
                    "actual_output": tr.actual_output,
                    "passed": tr.passed,
                    "error": tr.error,
                    "execution_time_ms": tr.execution_time_ms
                }
                for tr in self.test_results
            ],
            "metrics": {
                "total_execution_time_ms": self.metrics.total_execution_time_ms,
                "memory_used_mb": self.metrics.memory_used_mb,
                "cpu_time_ms": self.metrics.cpu_time_ms,
                "container_startup_time_ms": self.metrics.container_startup_time_ms,
                "code_execution_time_ms": self.metrics.code_execution_time_ms,
                "timestamp": self.metrics.timestamp
            },
            "summary": {
                "total_tests": len(self.test_results),
                "tests_passed": self.tests_passed_count,
                "tests_failed": self.tests_failed_count,
                "all_passed": self.all_tests_passed
            }
        }



