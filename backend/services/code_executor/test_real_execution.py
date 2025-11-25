"""
Test Real Code Execution with Available Docker Image

This tests actual code execution using the Python Docker image that's available.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.code_executor import CodeExecutor, ExecutionRequest, TestCase, Language


def test_simple_execution():
    """Test 1: Simple print statement"""
    print("\n" + "="*80)
    print("TEST 1: Simple Print Statement")
    print("="*80)
    
    executor = CodeExecutor()
    
    code = """print("Hello from real Docker execution!")"""
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    print(f"✓ Output: {result.stdout}")
    
    return result.status.value == "success"


def test_with_input():
    """Test 2: Code with input"""
    print("\n" + "="*80)
    print("TEST 2: Code with Input (Add Two Numbers)")
    print("="*80)
    
    executor = CodeExecutor()
    
    code = """
a = int(input())
b = int(input())
print(a + b)
"""
    
    test_cases = [
        TestCase(input="5\n3", expected_output="8"),
        TestCase(input="10\n20", expected_output="30"),
        TestCase(input="-5\n5", expected_output="0"),
    ]
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        test_cases=test_cases,
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Tests Passed: {result.tests_passed_count}/{len(result.test_results)}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    
    for i, test in enumerate(result.test_results, 1):
        status = "✓ PASS" if test.passed else "✗ FAIL"
        print(f"\n  Test {i}: {status}")
        print(f"    Input: {test.input}")
        print(f"    Expected: {test.expected_output}")
        print(f"    Got: {test.actual_output}")
    
    return result.all_tests_passed


def test_two_sum_correct():
    """Test 3: Two Sum Correct Solution"""
    print("\n" + "="*80)
    print("TEST 3: Two Sum - Correct Solution")
    print("="*80)
    
    executor = CodeExecutor()
    
    # Load the correct solution
    demo_dir = Path(__file__).parent / "demo_problems"
    with open(demo_dir / "two_sum_correct.py", 'r') as f:
        code = f.read()
    
    test_cases = [
        TestCase(input="2,7,11,15\n9", expected_output="[0, 1]"),
        TestCase(input="3,2,4\n6", expected_output="[1, 2]"),
        TestCase(input="3,3\n6", expected_output="[0, 1]"),
    ]
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        test_cases=test_cases,
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Tests Passed: {result.tests_passed_count}/{len(result.test_results)}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    
    for i, test in enumerate(result.test_results, 1):
        status = "✓ PASS" if test.passed else "✗ FAIL"
        print(f"\n  Test {i}: {status}")
        print(f"    Input: {test.input[:30]}...")
        print(f"    Expected: {test.expected_output}")
        print(f"    Got: {test.actual_output}")
    
    return result.all_tests_passed


def test_two_sum_wrong():
    """Test 4: Two Sum Wrong Solution"""
    print("\n" + "="*80)
    print("TEST 4: Two Sum - Wrong Solution (Should Fail)")
    print("="*80)
    
    executor = CodeExecutor()
    
    # Load the wrong solution
    demo_dir = Path(__file__).parent / "demo_problems"
    with open(demo_dir / "two_sum_wrong.py", 'r') as f:
        code = f.read()
    
    test_cases = [
        TestCase(input="2,7,11,15\n9", expected_output="[0, 1]"),
        TestCase(input="3,2,4\n6", expected_output="[1, 2]"),
        TestCase(input="-1,-2,-3,-4,-5\n-8", expected_output="[2, 4]"),
    ]
    
    request = ExecutionRequest(
        code=code,
        language=Language.PYTHON,
        test_cases=test_cases,
        timeout=10
    )
    
    result = executor.execute(request)
    
    print(f"\n✓ Status: {result.status.value}")
    print(f"✓ Tests Passed: {result.tests_passed_count}/{len(result.test_results)}")
    print(f"✓ Tests Failed: {result.tests_failed_count}/{len(result.test_results)}")
    print(f"✓ Execution Time: {result.metrics.total_execution_time_ms:.2f}ms")
    
    for i, test in enumerate(result.test_results, 1):
        status = "✓ PASS" if test.passed else "✗ FAIL"
        print(f"\n  Test {i}: {status}")
        print(f"    Input: {test.input[:30]}...")
        print(f"    Expected: {test.expected_output}")
        print(f"    Got: {test.actual_output}")
        if not test.passed:
            print(f"    ❌ Bug: {test.error or 'Output mismatch'}")
    
    # For wrong solution, we expect failures
    return result.tests_failed_count > 0


def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                   REAL CODE EXECUTION TEST                                   ║
║                   Using Docker: python:3.11-slim                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        ("Simple Execution", test_simple_execution),
        ("Input/Output", test_with_input),
        ("Two Sum Correct", test_two_sum_correct),
        ("Two Sum Wrong", test_two_sum_wrong),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n❌ Error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    
    for test_name, passed, error in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"\n{status}: {test_name}")
        if error:
            print(f"  Error: {error}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Docker execution is working perfectly!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    main()



