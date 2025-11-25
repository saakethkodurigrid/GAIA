"""
Example usage of the Code Executor Service

This demonstrates how to use the code executor in your application.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.code_executor import CodeExecutor, ExecutionRequest, TestCase, Language


def example_1_simple_execution():
    """Example 1: Simple code execution without test cases"""
    print("\n" + "="*70)
    print("Example 1: Simple Python Execution")
    print("="*70)
    
    executor = CodeExecutor()
    
    code = """
# Calculate factorial
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(f"Factorial of 5 is: {factorial(5)}")
print(f"Factorial of 10 is: {factorial(10)}")
"""
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    print(f"\n📤 Output:\n{result.stdout}")


def example_2_with_test_cases():
    """Example 2: Code execution with test cases"""
    print("\n" + "="*70)
    print("Example 2: Python with Test Cases")
    print("="*70)
    
    executor = CodeExecutor()
    
    code = """
# Sum of array elements
arr = list(map(int, input().split()))
print(sum(arr))
"""
    
    test_cases = [
        TestCase(input="1 2 3 4 5", expected_output="15"),
        TestCase(input="10 20 30", expected_output="60"),
        TestCase(input="100", expected_output="100"),
    ]
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        test_cases=test_cases,
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    print(f"\n📊 Test Results:")
    print(f"   Total: {len(result.test_results)}")
    print(f"   Passed: {result.tests_passed_count} ✓")
    print(f"   Failed: {result.tests_failed_count} ✗")
    
    for i, test_result in enumerate(result.test_results, 1):
        status = "✓" if test_result.passed else "✗"
        print(f"\n   Test {i}: {status}")
        print(f"      Input: {test_result.input}")
        print(f"      Expected: {test_result.expected_output}")
        print(f"      Actual: {test_result.actual_output}")


def example_3_javascript():
    """Example 3: JavaScript execution"""
    print("\n" + "="*70)
    print("Example 3: JavaScript Execution")
    print("="*70)
    
    executor = CodeExecutor()
    
    code = """
// Calculate square of numbers
const numbers = [1, 2, 3, 4, 5];
const squares = numbers.map(n => n * n);
console.log(squares.join(' '));
"""
    
    request = ExecutionRequest(
        code=code,
        language=Language.JAVASCRIPT,
        test_cases=[
            TestCase(input="", expected_output="1 4 9 16 25")
        ],
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Output: {result.stdout}")
    print(f"✓ All Tests Passed: {result.all_tests_passed}")


def example_4_java():
    """Example 4: Java execution with compilation"""
    print("\n" + "="*70)
    print("Example 4: Java Execution")
    print("="*70)
    
    executor = CodeExecutor()
    
    code = """
public class Main {
    public static void main(String[] args) {
        System.out.println("Java is working!");
        
        // Calculate sum
        int sum = 0;
        for (int i = 1; i <= 100; i++) {
            sum += i;
        }
        System.out.println("Sum of 1 to 100: " + sum);
    }
}
"""
    
    request = ExecutionRequest(
        code=code,
        language=Language.JAVA,
        timeout=15  # Java needs a bit more time for compilation
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    if result.compilation_output:
        print(f"✓ Compilation: Success")
    print(f"\n📤 Output:\n{result.stdout}")


def example_5_detailed_metrics():
    """Example 5: Detailed execution metrics"""
    print("\n" + "="*70)
    print("Example 5: Detailed Metrics")
    print("="*70)
    
    executor = CodeExecutor()
    
    code = """
import time
print("Starting computation...")
time.sleep(0.1)  # Simulate some work
result = sum(range(1000000))
print(f"Result: {result}")
"""
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        timeout=10,
        memory_limit=128
    )
    
    result = executor.execute(request)
    
    print(f"\n📊 Detailed Metrics:")
    print(f"   Execution ID: {result.execution_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Total Time: {result.metrics.total_execution_time_ms:.2f}ms")
    print(f"   Code Execution Time: {result.metrics.code_execution_time_ms:.2f}ms")
    print(f"   Container Startup Time: {result.metrics.container_startup_time_ms:.2f}ms")
    print(f"   Memory Used: {result.metrics.memory_used_mb:.2f}MB")
    print(f"   Timestamp: {result.metrics.timestamp}")
    print(f"\n   Output saved to: outputs/execution_*_{result.execution_id}/")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("  CODE EXECUTOR SERVICE - USAGE EXAMPLES")
    print("="*70)
    
    try:
        print("\nInitializing Code Executor...")
        
        # Run examples
        example_1_simple_execution()
        example_2_with_test_cases()
        example_3_javascript()
        example_4_java()
        example_5_detailed_metrics()
        
        print("\n" + "="*70)
        print("  All examples completed successfully!")
        print("="*70)
        print("\nCheck the 'outputs/' directory for detailed results.")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Docker is running and all dependencies are installed.")
        print("Run: python validate_service.py")


if __name__ == "__main__":
    main()



