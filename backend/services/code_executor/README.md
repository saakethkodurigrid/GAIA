# Code Executor Service

A secure, isolated code execution service supporting multiple programming languages.

## Features
- ✅ Multi-language support (Python, JavaScript, Java)
- ✅ Docker-based sandboxing for security
- ✅ Resource limits (CPU, memory, time)
- ✅ Test case execution and validation
- ✅ Detailed metrics and logging
- ✅ Output capture (stdout, stderr)

## Supported Languages
- Python 3.11
- JavaScript (Node.js 20)
- Java 17

## Installation

### Prerequisites
- Docker installed and running
- Python 3.8+

### Setup
```bash
# Install Python dependencies
pip install docker psutil

# Pull required Docker images
docker pull python:3.11-slim
docker pull node:20-slim
docker pull openjdk:17-slim
```

## Usage

### Run Tests
```bash
python test_executor.py
```

### Validate Service
```bash
python validate_service.py
```

## Output Structure
```
outputs/
├── execution_TIMESTAMP_ID/
│   ├── code.txt
│   ├── output.txt
│   ├── errors.txt
│   ├── metrics.json
│   └── logs.txt
```

## Security Features
- Process isolation via Docker containers
- Memory limits (256MB default)
- CPU limits (1 core)
- Execution timeout (30s default)
- Network disabled
- Read-only filesystem
- No privileged access



