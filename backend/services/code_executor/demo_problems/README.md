# LeetCode-Style Demo Problems

This folder contains a complete demonstration of the code executor working exactly like LeetCode, with side-by-side comparison of correct vs incorrect solutions.

## 📁 Files Structure

### Problem Definitions
- `two_sum_problem.json` - Two Sum problem with 6 test cases (3 visible, 3 hidden)
- `fibonacci_problem.json` - Fibonacci problem with 6 test cases

### Solutions
#### Two Sum:
- `two_sum_correct.py` - ✅ Correct solution (passes all tests)
- `two_sum_wrong.py` - ❌ Wrong solution (fails some tests due to bugs)

#### Fibonacci:
- `fibonacci_correct.py` - ✅ Correct solution (passes all tests)
- `fibonacci_wrong.py` - ❌ Wrong solution (off-by-one error)

### Runner
- `demo_runner.py` - Main script that runs both solutions and generates comparison reports

## 🚀 How to Run

### Quick Start
```bash
cd /Users/rabdin/Documents/GaiaPlat/GAIA/backend
source venv/bin/activate
python services/code_executor/demo_runner.py
```

### What It Does
1. Loads problem definitions (JSON)
2. Loads correct and wrong solutions
3. Executes both against all test cases
4. Generates 3-column comparison:
   - Test case input & expected output
   - Correct solution output
   - Wrong solution output
5. Creates multiple report formats:
   - **Text Report** (.txt) - ASCII table in terminal
   - **HTML Report** (.html) - Beautiful visual report
   - **CSV Report** (.csv) - Spreadsheet format

## 📊 Output Examples

### Console Output (ASCII Table)
```
==================================================================================================================
  LEETCODE-STYLE COMPARISON REPORT
  Problem: Two Sum (Easy)
==================================================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION SUMMARY                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Correct Solution:    6/6 tests passed ✓                                   │
│  Wrong Solution:      2/6 tests passed ✗                                   │
│                                                                              │
│  Execution Time:                                                            │
│    - Correct:  234.56 ms                                                    │
│    - Wrong:    245.78 ms                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────┬─────────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Test │ Input                   │ Expected Output  │ Correct Output   │ Wrong Output     │
├──────┼─────────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 1    │ 2,7,11,15 → 9          │ [0, 1]          │ [0, 1]         ✓ │ [1, 0]         ✗ │
│ 2    │ 3,2,4 → 6              │ [1, 2]          │ [1, 2]         ✓ │ [2, 1]         ✗ │
│ 3    │ 3,3 → 6                │ [0, 1]          │ [0, 1]         ✓ │ [1, 0]         ✗ │
│ 4    │ 1,5,3,7,2 → 9         │ [3, 4]          │ [3, 4]         ✓ │ [4, 3]         ✗ │
│ 5    │ 10,20,30,40 → 50      │ [1, 2]          │ [1, 2]         ✓ │ [2, 1]         ✗ │
│ 6    │ -1,-2,-3,-4,-5 → -8   │ [2, 4]          │ [2, 4]         ✓ │ []             ✗ │
└──────┴─────────────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### HTML Report
Beautiful web-based report with:
- Color-coded test results (green for pass, red for fail)
- Summary cards showing pass/fail rates
- Execution metrics (time, memory)
- Interactive table
- Responsive design

**Open in browser:** `comparison_outputs/two_sum_comparison.html`

### CSV Report
Spreadsheet-friendly format:
```csv
Problem,Two Sum
Difficulty,Easy

Solution Type,Tests Passed,Tests Failed,Total Tests,Time (ms),Memory (MB)
Correct Solution,6,0,6,234.56,12.50
Wrong Solution,2,4,6,245.78,13.20

Test ID,Input,Expected Output,Correct Output,Correct Status,Wrong Output,Wrong Status
1,2,7,11,15 → 9,[0, 1],[0, 1],PASS,[1, 0],FAIL
...
```

## 🐛 What Bugs Are in Wrong Solutions?

### Two Sum Wrong Solution
1. **Bug 1:** Returns indices in reversed order `[i, seen[complement]]` instead of `[seen[complement], i]`
2. **Bug 2:** Doesn't handle negative numbers (condition `if num > 0` excludes negatives)

**Result:** Fails 4 out of 6 test cases

### Fibonacci Wrong Solution
1. **Bug:** Off-by-one error in loop range `range(2, n)` instead of `range(2, n + 1)`

**Result:** Fails all test cases except n=0 and n=1

## 📋 Test Cases

### Two Sum
| Test | Input | Expected | Visibility |
|------|-------|----------|------------|
| 1 | [2,7,11,15], target=9 | [0,1] | Visible |
| 2 | [3,2,4], target=6 | [1,2] | Visible |
| 3 | [3,3], target=6 | [0,1] | Visible |
| 4 | [1,5,3,7,2], target=9 | [3,4] | Hidden |
| 5 | [10,20,30,40], target=50 | [1,2] | Hidden |
| 6 | [-1,-2,-3,-4,-5], target=-8 | [2,4] | Hidden |

### Fibonacci
| Test | Input | Expected | Visibility |
|------|-------|----------|------------|
| 1 | 0 | 0 | Visible |
| 2 | 1 | 1 | Visible |
| 3 | 5 | 5 | Visible |
| 4 | 10 | 55 | Hidden |
| 5 | 15 | 610 | Hidden |
| 6 | 20 | 6765 | Hidden |

## 🎯 Expected Results

### Correct Solutions
- **Two Sum:** ✅ 6/6 tests passed
- **Fibonacci:** ✅ 6/6 tests passed

### Wrong Solutions
- **Two Sum:** ❌ 2/6 tests passed (fails tests with order and negative numbers)
- **Fibonacci:** ❌ 2/6 tests passed (only n=0 and n=1 work)

## 🔍 Understanding the Output

### Three-Column Comparison
1. **Column 1:** Test case input and expected output (ground truth)
2. **Column 2:** Correct solution's output (should match expected)
3. **Column 3:** Wrong solution's output (shows where it fails)

### Status Indicators
- ✓ = Test passed
- ✗ = Test failed

### Hidden Test Cases
Problems include both visible and hidden test cases, just like LeetCode:
- **Visible:** Shown as examples to help understand the problem
- **Hidden:** Only revealed after submission to prevent hardcoding

## 💡 Use Cases

1. **Validate Executor** - Proves the executor works correctly
2. **Debug Solutions** - See exactly where code fails
3. **Test Quality** - Verify test cases catch bugs
4. **Demo System** - Show stakeholders how it works
5. **Education** - Help users understand their mistakes

## 🎨 Customization

### Add Your Own Problem
1. Create `problem_name_problem.json` with test cases
2. Create `problem_name_correct.py` with correct solution
3. Create `problem_name_wrong.py` with intentional bugs
4. Add to `demo_runner.py` demos list
5. Run the demo!

### Example Problem JSON Structure
```json
{
  "problem_id": 1,
  "title": "Problem Name",
  "difficulty": "Easy|Medium|Hard",
  "description": "Problem description...",
  "test_cases": [
    {
      "id": 1,
      "input": "input data",
      "expected_output": "expected output",
      "hidden": false
    }
  ]
}
```

## 📝 Notes

- All reports are saved to `comparison_outputs/` directory
- HTML reports are best viewed in a modern browser
- CSV reports can be opened in Excel or Google Sheets
- Text reports are great for terminal viewing
- Each run generates timestamped reports

## 🚀 Next Steps

1. Run the demo: `python demo_runner.py`
2. Open HTML reports in browser
3. Review the comparison tables
4. Add your own problems
5. Integrate into your backend API

---

**This demonstrates that the code executor works exactly like LeetCode!** ✨



