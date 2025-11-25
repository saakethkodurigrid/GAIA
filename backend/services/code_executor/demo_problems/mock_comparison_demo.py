"""
Mock LeetCode-Style Comparison Demo

This creates the comparison reports WITHOUT actually executing code.
Perfect for demonstration when Docker images aren't available.
"""

import json
from pathlib import Path
from datetime import datetime
import csv


def create_mock_results():
    """Create mock execution results"""
    
    # Two Sum problem - Correct results
    two_sum_correct = {
        "status": "success",
        "test_results": [
            {"test_id": 1, "input": "2,7,11,15\n9", "expected": "[0, 1]", "actual": "[0, 1]", "passed": True, "error": None, "time_ms": 45.23},
            {"test_id": 2, "input": "3,2,4\n6", "expected": "[1, 2]", "actual": "[1, 2]", "passed": True, "error": None, "time_ms": 42.15},
            {"test_id": 3, "input": "3,3\n6", "expected": "[0, 1]", "actual": "[0, 1]", "passed": True, "error": None, "time_ms": 43.87},
            {"test_id": 4, "input": "1,5,3,7,2\n9", "expected": "[3, 4]", "actual": "[3, 4]", "passed": True, "error": None, "time_ms": 48.92},
            {"test_id": 5, "input": "10,20,30,40\n50", "expected": "[1, 2]", "actual": "[1, 2]", "passed": True, "error": None, "time_ms": 44.56},
            {"test_id": 6, "input": "-1,-2,-3,-4,-5\n-8", "expected": "[2, 4]", "actual": "[2, 4]", "passed": True, "error": None, "time_ms": 46.78},
        ],
        "metrics": {"total_time_ms": 271.51, "memory_mb": 12.5},
        "summary": {"total": 6, "passed": 6, "failed": 0}
    }
    
    # Two Sum problem - Wrong results (with bugs)
    two_sum_wrong = {
        "status": "failed",
        "test_results": [
            {"test_id": 1, "input": "2,7,11,15\n9", "expected": "[0, 1]", "actual": "[1, 0]", "passed": False, "error": None, "time_ms": 47.12},
            {"test_id": 2, "input": "3,2,4\n6", "expected": "[1, 2]", "actual": "[2, 1]", "passed": False, "error": None, "time_ms": 45.89},
            {"test_id": 3, "input": "3,3\n6", "expected": "[0, 1]", "actual": "[1, 0]", "passed": False, "error": None, "time_ms": 44.23},
            {"test_id": 4, "input": "1,5,3,7,2\n9", "expected": "[3, 4]", "actual": "[4, 3]", "passed": False, "error": None, "time_ms": 49.34},
            {"test_id": 5, "input": "10,20,30,40\n50", "expected": "[1, 2]", "actual": "[2, 1]", "passed": False, "error": None, "time_ms": 46.67},
            {"test_id": 6, "input": "-1,-2,-3,-4,-5\n-8", "expected": "[2, 4]", "actual": "[]", "passed": False, "error": "Negative numbers not handled", "time_ms": 42.11},
        ],
        "metrics": {"total_time_ms": 275.36, "memory_mb": 13.2},
        "summary": {"total": 6, "passed": 0, "failed": 6}
    }
    
    # Fibonacci problem - Correct results
    fibonacci_correct = {
        "status": "success",
        "test_results": [
            {"test_id": 1, "input": "0", "expected": "0", "actual": "0", "passed": True, "error": None, "time_ms": 38.45},
            {"test_id": 2, "input": "1", "expected": "1", "actual": "1", "passed": True, "error": None, "time_ms": 39.12},
            {"test_id": 3, "input": "5", "expected": "5", "actual": "5", "passed": True, "error": None, "time_ms": 41.23},
            {"test_id": 4, "input": "10", "expected": "55", "actual": "55", "passed": True, "error": None, "time_ms": 43.56},
            {"test_id": 5, "input": "15", "expected": "610", "actual": "610", "passed": True, "error": None, "time_ms": 45.89},
            {"test_id": 6, "input": "20", "expected": "6765", "actual": "6765", "passed": True, "error": None, "time_ms": 48.12},
        ],
        "metrics": {"total_time_ms": 256.37, "memory_mb": 11.8},
        "summary": {"total": 6, "passed": 6, "failed": 0}
    }
    
    # Fibonacci problem - Wrong results (off-by-one error)
    fibonacci_wrong = {
        "status": "failed",
        "test_results": [
            {"test_id": 1, "input": "0", "expected": "0", "actual": "0", "passed": True, "error": None, "time_ms": 39.23},
            {"test_id": 2, "input": "1", "expected": "1", "actual": "1", "passed": True, "error": None, "time_ms": 40.11},
            {"test_id": 3, "input": "5", "expected": "5", "actual": "3", "passed": False, "error": "Off-by-one error", "time_ms": 42.34},
            {"test_id": 4, "input": "10", "expected": "55", "actual": "34", "passed": False, "error": "Off-by-one error", "time_ms": 44.56},
            {"test_id": 5, "input": "15", "expected": "610", "actual": "377", "passed": False, "error": "Off-by-one error", "time_ms": 46.78},
            {"test_id": 6, "input": "20", "expected": "6765", "actual": "4181", "passed": False, "error": "Off-by-one error", "time_ms": 49.01},
        ],
        "metrics": {"total_time_ms": 262.03, "memory_mb": 12.1},
        "summary": {"total": 6, "passed": 2, "failed": 4}
    }
    
    return {
        "two_sum": (two_sum_correct, two_sum_wrong),
        "fibonacci": (fibonacci_correct, fibonacci_wrong)
    }


def generate_comparison_table(problem, correct_result, wrong_result):
    """Generate ASCII comparison table"""
    
    table = f"""
{'='*120}
  LEETCODE-STYLE COMPARISON REPORT
  Problem: {problem['title']} ({problem['difficulty']})
{'='*120}

"""
    
    # Summary
    table += f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION SUMMARY                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ✅ Correct Solution:    {correct_result['summary']['passed']}/{correct_result['summary']['total']} tests passed                                      │
│  ❌ Wrong Solution:      {wrong_result['summary']['passed']}/{wrong_result['summary']['total']} tests passed                                      │
│                                                                              │
│  ⏱️  Execution Time:                                                         │
│     - Correct:  {correct_result['metrics']['total_time_ms']:>6.2f} ms                                              │
│     - Wrong:    {wrong_result['metrics']['total_time_ms']:>6.2f} ms                                              │
│                                                                              │
│  💾 Memory Usage:                                                            │
│     - Correct:  {correct_result['metrics']['memory_mb']:>6.2f} MB                                              │
│     - Wrong:    {wrong_result['metrics']['memory_mb']:>6.2f} MB                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

"""
    
    # Test results table
    table += """
┌──────┬─────────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Test │ Input                   │ Expected Output  │ Correct Output   │ Wrong Output     │
├──────┼─────────────────────────┼──────────────────┼──────────────────┼──────────────────┤
"""
    
    for tc in problem['test_cases']:
        test_id = tc['id']
        input_str = tc['input'].replace('\n', ' → ')[:23]
        expected = tc['expected_output'][:16]
        
        correct_test = next((t for t in correct_result['test_results'] if t['test_id'] == test_id), None)
        wrong_test = next((t for t in wrong_result['test_results'] if t['test_id'] == test_id), None)
        
        correct_output = correct_test['actual'][:16] if correct_test else 'N/A'
        wrong_output = wrong_test['actual'][:16] if wrong_test else 'N/A'
        
        correct_status = '✓' if correct_test and correct_test['passed'] else '✗'
        wrong_status = '✓' if wrong_test and wrong_test['passed'] else '✗'
        
        hidden = '[H]' if tc.get('hidden', False) else '   '
        
        table += f"│ {test_id:<2}{hidden} │ {input_str:<23} │ {expected:<16} │ {correct_output:<14} {correct_status} │ {wrong_output:<14} {wrong_status} │\n"
    
    table += "└──────┴─────────────────────────┴──────────────────┴──────────────────┴──────────────────┘\n"
    
    # Failure analysis
    failures = [t for t in wrong_result['test_results'] if not t['passed']]
    if failures:
        table += "\n\n┌─────────────────────────────────────────────────────────────────────────────┐\n"
        table += "│ ❌ DETAILED FAILURE ANALYSIS (Wrong Solution)                               │\n"
        table += "└─────────────────────────────────────────────────────────────────────────────┘\n\n"
        
        for test in failures:
            table += f"🔴 Test Case {test['test_id']}: FAILED\n"
            table += f"   Input:    {test['input']}\n"
            table += f"   Expected: {test['expected']}\n"
            table += f"   Got:      {test['actual']}\n"
            if test['error']:
                table += f"   Error:    {test['error']}\n"
            table += f"   Time:     {test['time_ms']:.2f}ms\n\n"
    
    # Success summary
    if correct_result['summary']['passed'] == correct_result['summary']['total']:
        table += "\n✅ CORRECT SOLUTION: ALL TESTS PASSED!\n"
    
    if wrong_result['summary']['passed'] < wrong_result['summary']['total']:
        table += f"\n❌ WRONG SOLUTION: FAILED {wrong_result['summary']['failed']}/{wrong_result['summary']['total']} TESTS\n"
    
    table += "\n" + "="*120 + "\n"
    
    return table


def main():
    """Generate mock comparison reports"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                   LEETCODE-STYLE COMPARISON DEMO                             ║
║                   (Mock Results - No Docker Required)                        ║
║                                                                              ║
║  This demo shows side-by-side comparison of correct vs wrong solutions      ║
║  with detailed test results in 3-column format                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Load problems
    demo_dir = Path(__file__).parent
    output_dir = demo_dir / "comparison_outputs"
    output_dir.mkdir(exist_ok=True)
    
    with open(demo_dir / "two_sum_problem.json") as f:
        two_sum_problem = json.load(f)
    
    with open(demo_dir / "fibonacci_problem.json") as f:
        fibonacci_problem = json.load(f)
    
    # Get mock results
    results = create_mock_results()
    
    # Generate reports for Two Sum
    print("\n" + "="*80)
    print("  Generating Two Sum Comparison...")
    print("="*80)
    
    correct, wrong = results['two_sum']
    table = generate_comparison_table(two_sum_problem, correct, wrong)
    
    # Save text report
    text_file = output_dir / "two_sum_comparison.txt"
    text_file.write_text(table)
    print(f"✓ Text report saved: {text_file}")
    
    # Print to console
    print(table)
    
    # Generate reports for Fibonacci
    print("\n" + "="*80)
    print("  Generating Fibonacci Comparison...")
    print("="*80)
    
    correct, wrong = results['fibonacci']
    table = generate_comparison_table(fibonacci_problem, correct, wrong)
    
    # Save text report
    text_file = output_dir / "fibonacci_comparison.txt"
    text_file.write_text(table)
    print(f"✓ Text report saved: {text_file}")
    
    # Print to console
    print(table)
    
    # Summary
    print("\n" + "="*80)
    print("  DEMO COMPLETE!")
    print("="*80)
    print(f"\n📁 All reports saved to: {output_dir}")
    print("\n📊 Summary:")
    print("  • Two Sum:")
    print("     - Correct: 6/6 tests passed ✅")
    print("     - Wrong:   0/6 tests passed ❌ (reversed indices + negative number bug)")
    print("\n  • Fibonacci:")
    print("     - Correct: 6/6 tests passed ✅")
    print("     - Wrong:   2/6 tests passed ❌ (off-by-one error in loop)")
    print("\n💡 This demonstrates how the executor catches bugs in code!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()



