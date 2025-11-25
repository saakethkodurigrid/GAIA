"""
Configuration for code executor service
"""
import os
from typing import Dict


class ExecutorConfig:
    """Configuration for code executor"""
    
    # Output directory for execution results
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
    
    # Docker image configurations
    DOCKER_IMAGES: Dict[str, str] = {
        "python": "python:3.11-slim",
        "javascript": "node:20-slim",
        "java": "openjdk:17-slim"
    }
    
    # Default resource limits
    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_MEMORY_LIMIT = 256  # MB
    DEFAULT_CPU_LIMIT = 1.0  # CPU cores
    
    # Language-specific configurations
    LANGUAGE_CONFIGS = {
        "python": {
            "file_extension": ".py",
            "compile_command": None,  # Python is interpreted
            "run_command": "python3 /code/main.py",
            "docker_image": "python:3.11-slim"
        },
        "javascript": {
            "file_extension": ".js",
            "compile_command": None,  # JavaScript is interpreted
            "run_command": "node /code/main.js",
            "docker_image": "node:20-slim"
        },
        "java": {
            "file_extension": ".java",
            "compile_command": "javac /code/Main.java",
            "run_command": "java -cp /code Main",
            "docker_image": "openjdk:17-slim",
            "main_class": "Main"
        }
    }
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Security settings
    ENABLE_NETWORK = False  # Disable network access in containers
    READ_ONLY_FILESYSTEM = True  # Make filesystem read-only
    DROP_CAPABILITIES = True  # Drop all Linux capabilities
    
    @classmethod
    def ensure_output_dir(cls):
        """Ensure output directory exists"""
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
    
    @classmethod
    def get_language_config(cls, language: str) -> Dict:
        """Get configuration for a specific language"""
        return cls.LANGUAGE_CONFIGS.get(language.lower(), {})



