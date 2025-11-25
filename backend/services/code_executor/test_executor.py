"""
Test file for code executor service

This script tests the code executor with various test cases across
different programming languages.
"""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.code_executor import CodeExecutor, ExecutionRequest, TestCase, Language


# Test cases for different languages
TEST_CASES = {
    "python": {
        "simple_print": {
            "code": """print("Hello, World!")""",
            "test_cases": [],
            "description": "Simple print statement"
        },
        "add_numbers": {
            "code": """
a = int(input())
b = int(input())
print(a + b)
""",
            "test_cases": [
                TestCase(input="5\n3", expected_output="8"),
                TestCase(input="10\n20", expected_output="30"),
                TestCase(input="-5\n5", expected_output="0"),
            ],
            "description": "Add two numbers from input"
        },
        "fibonacci": {
            "code": """
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

n = int(input())
print(fibonacci(n))
""",
            "test_cases": [
                TestCase(input="0", expected_output="0"),
                TestCase(input="1", expected_output="1"),
                TestCase(input="5", expected_output="5"),
                TestCase(input="10", expected_output="55"),
            ],
            "description": "Calculate Fibonacci number"
        },
        "error_case": {
            "code": """
x = 10 / 0
print(x)
""",
            "test_cases": [],
            "description": "Runtime error (division by zero)"
        }
    },
    "javascript": {
        "simple_log": {
            "code": """console.log("Hello, JavaScript!");""",
            "test_cases": [],
            "description": "Simple console.log"
        },
        "multiply_numbers": {
            "code": """
const readline = require('readline');
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

const lines = [];
rl.on('line', (line) => {
    lines.push(line);
});

rl.on('close', () => {
    const a = parseInt(lines[0]);
    const b = parseInt(lines[1]);
    console.log(a * b);
});
""",
            "test_cases": [
                TestCase(input="5\n3", expected_output="15"),
                TestCase(input="10\n4", expected_output="40"),
            ],
            "description": "Multiply two numbers"
        },
        "array_sum": {
            "code": """
const readline = require('readline');
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

const lines = [];
rl.on('line', (line) => {
    lines.push(line);
});

rl.on('close', () => {
    const arr = lines[0].split(' ').map(Number);
    const sum = arr.reduce((a, b) => a + b, 0);
    console.log(sum);
});
""",
            "test_cases": [
                TestCase(input="1 2 3 4 5", expected_output="15"),
                TestCase(input="10 20 30", expected_output="60"),
            ],
            "description": "Sum array elements"
        }
    },
    "java": {
        "simple_hello": {
            "code": """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, Java!");
    }
}
""",
            "test_cases": [],
            "description": "Simple Hello World"
        },
        "add_numbers": {
            "code": """
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int a = scanner.nextInt();
        int b = scanner.nextInt();
        System.out.println(a + b);
        scanner.close();
    }
}
""",
            "test_cases": [
                TestCase(input="5\n3", expected_output="8"),
                TestCase(input="100\n200", expected_output="300"),
            ],
            "description": "Add two integers"
        },
        "compilation_error": {
            "code": """
public class Main {
    public static void main(String[] args) {
        System.out.println("Missing semicolon")
    }
}
""",
            "test_cases": [],
            "description": "Compilation error (missing semicolon)"
        }
    }
}


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_subheader(text: str):
    """Print formatted subheader"""
    print("\n" + "-" * 70)
    print(f"  {text}")
    print("-" * 70)


def print_result(result):
    """Print execution result"""
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Execution ID: {result.execution_id}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    print(f"✓ Memory Used: {result.metrics.memory_used_mb:.2f}MB")
    
    if result.stdout:
        print(f"\n📤 Output:\n{result.stdout}")
    
    if result.stderr:
        print(f"\n⚠️  Errors:\n{result.stderr}")
    
    if result.compilation_output:
        print(f"\n🔨 Compilation Output:\n{result.compilation_output}")
    
    if result.test_results:
        print(f"\n📊 Test Results:")
        print(f"   Total: {len(result.test_results)}")
        print(f"   Passed: {result.tests_passed_count} ✓")
        print(f"   Failed: {result.tests_failed_count} ✗")
        
        for i, test_result in enumerate(result.test_results, 1):
            status = "✓ PASSED" if test_result.passed else "✗ FAILED"
            print(f"\n   Test {i}: {status}")
            print(f"      Input: {test_result.input}")
            print(f"      Expected: {test_result.expected_output}")
            print(f"      Actual: {test_result.actual_output}")
            print(f"      Time: {test_result.execution_time_ms:.2f}ms")
            if test_result.error:
                print(f"      Error: {test_result.error}")


def run_tests():
    """Run all test cases"""
    print_header("CODE EXECUTOR TEST SUITE")
    print("\nInitializing Code Executor...")
    
    try:
        executor = CodeExecutor()
        print("✓ Code Executor initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Code Executor: {e}")
        print("\nMake sure Docker is installed and running!")
        return
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    # Run tests for each language
    for language, test_suite in TEST_CASES.items():
        print_header(f"TESTING {language.upper()}")
        
        for test_name, test_data in test_suite.items():
            print_subheader(f"{test_name}: {test_data['description']}")
            total_tests += 1
            
            try:
                # Create execution request
                request = ExecutionRequest(
                    code=test_data["code"],
                    language=Language(language),
                    test_cases=test_data["test_cases"],
                    timeout=10,
                    memory_limit=256
                )
                
                # Execute
                print(f"\n⚙️  Executing {language} code...")
                start = time.time()
                result = executor.execute(request)
                duration = time.time() - start
                
                print(f"⏱️  Total duration: {duration:.2f}s")
                
                # Print results
                print_result(result)
                
                # Check if test passed
                if result.status.value in ["success", "failed"]:
                    if not test_data["test_cases"] or result.all_tests_passed:
                        passed_tests += 1
                        print("\n✅ TEST PASSED")
                    else:
                        failed_tests += 1
                        print("\n❌ TEST FAILED")
                else:
                    # Compilation errors or other errors are expected for some tests
                    if "error" in test_name.lower():
                        passed_tests += 1
                        print("\n✅ TEST PASSED (Expected error occurred)")
                    else:
                        failed_tests += 1
                        print("\n❌ TEST FAILED")
                
            except Exception as e:
                failed_tests += 1
                print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            
            time.sleep(0.5)  # Small delay between tests
    
    # Print summary
    print_header("TEST SUMMARY")
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✓")
    print(f"Failed: {failed_tests} ✗")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_tests()



