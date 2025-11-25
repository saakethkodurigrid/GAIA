# Quick Start Guide

Get started with the Code Executor Service in 5 minutes!

## Prerequisites

- ✅ Docker installed and running
- ✅ Python 3.8+
- ✅ pip package manager

## Installation

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/rabdin/Documents/GaiaPlat/GAIA/backend/services/code_executor

# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install docker psutil

# 2. Pull Docker images
docker pull python:3.11-slim
docker pull node:20-slim
docker pull openjdk:17-slim

# 3. Create output directory
mkdir -p outputs

# 4. Validate installation
python validate_service.py
```

## Usage

### Running Tests

```bash
# Run all test cases
python test_executor.py
```

This will execute test cases for:
- Python (simple print, math operations, fibonacci, error handling)
- JavaScript (console.log, input/output, array operations)
- Java (Hello World, arithmetic, compilation errors)

### Using in Your Code

```python
from services.code_executor import CodeExecutor, ExecutionRequest, TestCase, Language

# Initialize executor
executor = CodeExecutor()

# Create request
request = ExecutionRequest(
    code='print("Hello, World!")',
    language=Language.PYTHON,
    test_cases=[
        TestCase(input="", expected_output="Hello, World!")
    ],
    timeout=10,
    memory_limit=256
)

# Execute
result = executor.execute(request)

# Check results
print(f"Status: {result.status}")
print(f"Output: {result.stdout}")
print(f"Tests Passed: {result.tests_passed_count}/{len(result.test_results)}")
print(f"Execution Time: {result.metrics.total_execution_time_ms}ms")
```

## Validating Service

```bash
# Run comprehensive validation
python validate_service.py
```

This checks:
- Python environment
- Docker installation and daemon
- Required Docker images
- File structure
- Service functionality
- System resources

## Output Files

All execution results are saved to `outputs/` directory:

```
outputs/
└── execution_20241112_143022_abc123/
    ├── code.txt              # Submitted code
    ├── output.txt            # stdout
    ├── errors.txt            # stderr
    ├── metrics.json          # Detailed metrics and test results
    └── logs.txt              # Execution logs
```

## Example Test Results

```
Status: success
Execution Time: 234.56ms
Memory Used: 12.5MB
Tests Passed: 3/3 ✓

Test 1: PASSED ✓
  Input: 5\n3
  Expected: 8
  Actual: 8
  Time: 78.23ms
```

## Troubleshooting

### Docker not found
```bash
# Install Docker from: https://docs.docker.com/get-docker/
```

### Docker daemon not running
```bash
# macOS: Start Docker Desktop
# Linux: sudo systemctl start docker
```

### Permission denied
```bash
# macOS/Linux
chmod +x setup.sh

# Or add user to docker group (Linux)
sudo usermod -aG docker $USER
```

### Image pull failed
```bash
# Check internet connection and try manually:
docker pull python:3.11-slim
docker pull node:20-slim
docker pull openjdk:17-slim
```

## Configuration

Edit `config.py` to customize:

- Memory limits
- CPU limits
- Timeout values
- Docker images
- Output directory

## Security Features

✅ Process isolation via Docker
✅ Memory limits (256MB default)
✅ CPU limits (1 core)
✅ Execution timeout (30s)
✅ Network disabled
✅ Read-only filesystem
✅ No privileged access

## Next Steps

1. ✅ Run `./setup.sh` to install
2. ✅ Run `python test_executor.py` to test
3. ✅ Check `outputs/` for results
4. ✅ Integrate into your FastAPI backend
5. ✅ Add API endpoints for code execution

## Support

For issues or questions:
- Check validation report: `outputs/validation_report_*.json`
- Review logs in output folders
- Ensure Docker is running and accessible



