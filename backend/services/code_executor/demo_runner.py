"""
LeetCode-Style Demo Runner

This script demonstrates the code executor working like LeetCode:
1. Loads problem definitions with test cases
2. Runs correct and incorrect solutions
3. Generates a side-by-side comparison report
4. Creates visual HTML report and CSV output
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import csv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.code_executor import CodeExecutor, ExecutionRequest, TestCase, Language


class LeetCodeStyleRunner:
    """Runs solutions and generates comparison reports"""
    
    def __init__(self):
        self.executor = CodeExecutor()
        self.demo_dir = Path(__file__).parent / "demo_problems"
        self.output_dir = self.demo_dir / "comparison_outputs"
        self.output_dir.mkdir(exist_ok=True)
    
    def load_problem(self, problem_file: str) -> Dict[str, Any]:
        """Load problem definition from JSON"""
        with open(self.demo_dir / problem_file, 'r') as f:
            return json.load(f)
    
    def load_solution(self, solution_file: str) -> str:
        """Load solution code from file"""
        with open(self.demo_dir / solution_file, 'r') as f:
            return f.read()
    
    def run_solution(self, code: str, test_cases: List[Dict]) -> Dict:
        """Run solution against test cases"""
        # Convert test cases
        test_case_objects = [
            TestCase(
                input=tc["input"],
                expected_output=tc["expected_output"],
                test_id=tc["id"]
            )
            for tc in test_cases
        ]
        
        # Execute
        request = ExecutionRequest(
            code=code,
            language=Language.PYTHON,
            test_cases=test_case_objects,
            timeout=10,
            memory_limit=256
        )
        
        result = self.executor.execute(request)
        
        return {
            "status": result.status.value,
            "test_results": [
                {
                    "test_id": tr.test_id,
                    "input": tr.input,
                    "expected": tr.expected_output,
                    "actual": tr.actual_output,
                    "passed": tr.passed,
                    "error": tr.error,
                    "time_ms": tr.execution_time_ms
                }
                for tr in result.test_results
            ],
            "metrics": {
                "total_time_ms": result.metrics.total_execution_time_ms,
                "memory_mb": result.metrics.memory_used_mb
            },
            "summary": {
                "total": len(result.test_results),
                "passed": result.tests_passed_count,
                "failed": result.tests_failed_count
            }
        }
    
    def generate_comparison_table(self, problem: Dict, correct_result: Dict, wrong_result: Dict) -> str:
        """Generate ASCII comparison table"""
        
        # Header
        table = f"""
{'='*120}
  LEETCODE-STYLE COMPARISON REPORT
  Problem: {problem['title']} ({problem['difficulty']})
{'='*120}

"""
        
        # Summary Section
        table += f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION SUMMARY                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Correct Solution:    {correct_result['summary']['passed']}/{correct_result['summary']['total']} tests passed ✓                                  │
│  Wrong Solution:      {wrong_result['summary']['passed']}/{wrong_result['summary']['total']} tests passed ✗                                  │
│                                                                              │
│  Execution Time:                                                            │
│    - Correct:  {correct_result['metrics']['total_time_ms']:>6.2f} ms                                                │
│    - Wrong:    {wrong_result['metrics']['total_time_ms']:>6.2f} ms                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

"""
        
        # Test Case Comparison Table
        table += f"""
┌──────┬─────────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Test │ Input                   │ Expected Output  │ Correct Output   │ Wrong Output     │
├──────┼─────────────────────────┼──────────────────┼──────────────────┼──────────────────┤
"""
        
        for i, tc in enumerate(problem['test_cases']):
            test_id = tc['id']
            input_str = tc['input'].replace('\n', ' → ')[:23]
            expected = tc['expected_output'][:16]
            
            # Find corresponding results
            correct_test = next((t for t in correct_result['test_results'] if t['test_id'] == test_id), None)
            wrong_test = next((t for t in wrong_result['test_results'] if t['test_id'] == test_id), None)
            
            correct_output = correct_test['actual'][:16] if correct_test else 'N/A'
            wrong_output = wrong_test['actual'][:16] if wrong_test else 'N/A'
            
            # Status indicators
            correct_status = '✓' if correct_test and correct_test['passed'] else '✗'
            wrong_status = '✓' if wrong_test and wrong_test['passed'] else '✗'
            
            hidden = '[H]' if tc.get('hidden', False) else ''
            
            table += f"│ {test_id:<4} │ {input_str:<23} │ {expected:<16} │ {correct_output:<14} {correct_status} │ {wrong_output:<14} {wrong_status} │\n"
        
        table += "└──────┴─────────────────────────┴──────────────────┴──────────────────┴──────────────────┘\n"
        
        # Detailed Failures
        table += "\n\n┌─────────────────────────────────────────────────────────────────────────────┐\n"
        table += "│ DETAILED FAILURE ANALYSIS (Wrong Solution)                                  │\n"
        table += "└─────────────────────────────────────────────────────────────────────────────┘\n\n"
        
        for test in wrong_result['test_results']:
            if not test['passed']:
                table += f"Test Case {test['test_id']}: FAILED ✗\n"
                table += f"  Input:    {test['input']}\n"
                table += f"  Expected: {test['expected']}\n"
                table += f"  Got:      {test['actual']}\n"
                if test['error']:
                    table += f"  Error:    {test['error']}\n"
                table += "\n"
        
        table += "="*120 + "\n"
        
        return table
    
    def generate_html_report(self, problem: Dict, correct_result: Dict, wrong_result: Dict) -> str:
        """Generate HTML comparison report"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{problem['title']} - Comparison Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .summary {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .correct {{ border-left: 5px solid #4caf50; }}
        .wrong {{ border-left: 5px solid #f44336; }}
        .stats {{
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background: #333;
            color: white;
            padding: 15px;
            text-align: left;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .pass {{
            color: #4caf50;
            font-weight: bold;
        }}
        .fail {{
            color: #f44336;
            font-weight: bold;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-easy {{ background: #d4edda; color: #155724; }}
        .badge-medium {{ background: #fff3cd; color: #856404; }}
        .badge-hard {{ background: #f8d7da; color: #721c24; }}
        .code-block {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #667eea;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 {problem['title']}</h1>
        <p><span class="badge badge-{problem['difficulty'].lower()}">{problem['difficulty']}</span></p>
        <p>{problem['description']}</p>
        <small>Generated: {timestamp}</small>
    </div>
    
    <div class="summary">
        <div class="card correct">
            <h2>✅ Correct Solution</h2>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value pass">{correct_result['summary']['passed']}/{correct_result['summary']['total']}</div>
                    <div class="stat-label">Tests Passed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{correct_result['metrics']['total_time_ms']:.2f}</div>
                    <div class="stat-label">Time (ms)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{correct_result['metrics']['memory_mb']:.2f}</div>
                    <div class="stat-label">Memory (MB)</div>
                </div>
            </div>
        </div>
        
        <div class="card wrong">
            <h2>❌ Wrong Solution</h2>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value fail">{wrong_result['summary']['passed']}/{wrong_result['summary']['total']}</div>
                    <div class="stat-label">Tests Passed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{wrong_result['metrics']['total_time_ms']:.2f}</div>
                    <div class="stat-label">Time (ms)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{wrong_result['metrics']['memory_mb']:.2f}</div>
                    <div class="stat-label">Memory (MB)</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>📊 Test Cases Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Test #</th>
                    <th>Input</th>
                    <th>Expected</th>
                    <th>Correct Output</th>
                    <th>Wrong Output</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for tc in problem['test_cases']:
            test_id = tc['id']
            input_str = tc['input'].replace('\n', ' → ')
            expected = tc['expected_output']
            
            correct_test = next((t for t in correct_result['test_results'] if t['test_id'] == test_id), None)
            wrong_test = next((t for t in wrong_result['test_results'] if t['test_id'] == test_id), None)
            
            correct_output = correct_test['actual'] if correct_test else 'N/A'
            wrong_output = wrong_test['actual'] if wrong_test else 'N/A'
            
            correct_class = 'pass' if correct_test and correct_test['passed'] else 'fail'
            wrong_class = 'pass' if wrong_test and wrong_test['passed'] else 'fail'
            
            html += f"""
                <tr>
                    <td><strong>{test_id}</strong></td>
                    <td><code>{input_str}</code></td>
                    <td><code>{expected}</code></td>
                    <td class="{correct_class}"><code>{correct_output}</code></td>
                    <td class="{wrong_class}"><code>{wrong_output}</code></td>
                    <td>
                        <span class="{correct_class}">Correct: {'✓' if correct_test and correct_test['passed'] else '✗'}</span><br>
                        <span class="{wrong_class}">Wrong: {'✓' if wrong_test and wrong_test['passed'] else '✗'}</span>
                    </td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
    
    <div class="footer">
        <p>Generated by Code Executor Service | LeetCode-Style Comparison</p>
        <p>✅ = Test Passed | ❌ = Test Failed</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_csv_report(self, problem: Dict, correct_result: Dict, wrong_result: Dict, filename: str):
        """Generate CSV comparison report"""
        with open(self.output_dir / filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Problem', problem['title']])
            writer.writerow(['Difficulty', problem['difficulty']])
            writer.writerow([])
            
            # Summary
            writer.writerow(['Solution Type', 'Tests Passed', 'Tests Failed', 'Total Tests', 'Time (ms)', 'Memory (MB)'])
            writer.writerow([
                'Correct Solution',
                correct_result['summary']['passed'],
                correct_result['summary']['failed'],
                correct_result['summary']['total'],
                f"{correct_result['metrics']['total_time_ms']:.2f}",
                f"{correct_result['metrics']['memory_mb']:.2f}"
            ])
            writer.writerow([
                'Wrong Solution',
                wrong_result['summary']['passed'],
                wrong_result['summary']['failed'],
                wrong_result['summary']['total'],
                f"{wrong_result['metrics']['total_time_ms']:.2f}",
                f"{wrong_result['metrics']['memory_mb']:.2f}"
            ])
            writer.writerow([])
            
            # Test cases
            writer.writerow(['Test ID', 'Input', 'Expected Output', 'Correct Output', 'Correct Status', 'Wrong Output', 'Wrong Status'])
            
            for tc in problem['test_cases']:
                test_id = tc['id']
                input_str = tc['input'].replace('\n', ' → ')
                expected = tc['expected_output']
                
                correct_test = next((t for t in correct_result['test_results'] if t['test_id'] == test_id), None)
                wrong_test = next((t for t in wrong_result['test_results'] if t['test_id'] == test_id), None)
                
                correct_output = correct_test['actual'] if correct_test else 'N/A'
                wrong_output = wrong_test['actual'] if wrong_test else 'N/A'
                
                correct_status = 'PASS' if correct_test and correct_test['passed'] else 'FAIL'
                wrong_status = 'PASS' if wrong_test and wrong_test['passed'] else 'FAIL'
                
                writer.writerow([test_id, input_str, expected, correct_output, correct_status, wrong_output, wrong_status])
    
    def run_problem_demo(self, problem_name: str, correct_file: str, wrong_file: str):
        """Run complete demo for a problem"""
        print(f"\n{'='*80}")
        print(f"  Running Demo: {problem_name}")
        print(f"{'='*80}\n")
        
        # Load problem
        print("📋 Loading problem definition...")
        problem = self.load_problem(f"{problem_name}_problem.json")
        print(f"   Problem: {problem['title']} ({problem['difficulty']})")
        print(f"   Test Cases: {len(problem['test_cases'])}")
        
        # Load solutions
        print("\n📝 Loading solutions...")
        correct_code = self.load_solution(f"{problem_name}_correct.py")
        wrong_code = self.load_solution(f"{problem_name}_wrong.py")
        print("   ✓ Correct solution loaded")
        print("   ✓ Wrong solution loaded")
        
        # Run correct solution
        print("\n⚙️  Running correct solution...")
        correct_result = self.run_solution(correct_code, problem['test_cases'])
        print(f"   Result: {correct_result['summary']['passed']}/{correct_result['summary']['total']} tests passed")
        
        # Run wrong solution
        print("\n⚙️  Running wrong solution...")
        wrong_result = self.run_solution(wrong_code, problem['test_cases'])
        print(f"   Result: {wrong_result['summary']['passed']}/{wrong_result['summary']['total']} tests passed")
        
        # Generate reports
        print("\n📊 Generating comparison reports...")
        
        # ASCII table
        table = self.generate_comparison_table(problem, correct_result, wrong_result)
        table_file = self.output_dir / f"{problem_name}_comparison.txt"
        table_file.write_text(table)
        print(f"   ✓ Text report: {table_file}")
        
        # HTML report
        html = self.generate_html_report(problem, correct_result, wrong_result)
        html_file = self.output_dir / f"{problem_name}_comparison.html"
        html_file.write_text(html)
        print(f"   ✓ HTML report: {html_file}")
        
        # CSV report
        csv_file = f"{problem_name}_comparison.csv"
        self.generate_csv_report(problem, correct_result, wrong_result, csv_file)
        print(f"   ✓ CSV report: {self.output_dir / csv_file}")
        
        # Print table to console
        print(table)
        
        return {
            'problem': problem,
            'correct_result': correct_result,
            'wrong_result': wrong_result,
            'files': {
                'text': str(table_file),
                'html': str(html_file),
                'csv': str(self.output_dir / csv_file)
            }
        }


def main():
    """Run all demos"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                   LEETCODE-STYLE CODE EXECUTOR DEMO                          ║
║                                                                              ║
║  This demo shows the code executor working like LeetCode:                   ║
║  • Loads problem definitions with test cases                                ║
║  • Runs correct and incorrect solutions                                     ║
║  • Generates side-by-side comparison reports                                ║
║  • Creates HTML, CSV, and text output                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    runner = LeetCodeStyleRunner()
    
    # Run demos
    demos = [
        ("two_sum", "two_sum_correct", "two_sum_wrong"),
        ("fibonacci", "fibonacci_correct", "fibonacci_wrong"),
    ]
    
    results = []
    for problem_name, correct_file, wrong_file in demos:
        try:
            result = runner.run_problem_demo(problem_name, correct_file, wrong_file)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error running {problem_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n" + "="*80)
    print("  DEMO COMPLETE!")
    print("="*80)
    print(f"\n✅ Completed {len(results)} problem(s)")
    print(f"\n📁 All reports saved to: {runner.output_dir}")
    print("\nGenerated files:")
    for result in results:
        problem_name = result['problem']['title']
        print(f"\n  {problem_name}:")
        for file_type, file_path in result['files'].items():
            print(f"    • {file_type.upper()}: {file_path}")
    
    print("\n💡 Tip: Open the HTML files in your browser for best visualization!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

