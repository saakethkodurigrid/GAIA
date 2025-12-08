import type { CodingProblem } from '../types';

export const MOCK_CODING_PROBLEMS: CodingProblem[] = [
  {
    id: 1,
    title: 'Warehouse Box Organization',
    difficulty: 'Medium',
    description: 'A warehouse manager needs to organize boxes stored in a single row. Each box has a different weight, and they are positioned sequentially from position 0 to n-1. The manager has a forklift that can lift a group of three consecutive boxes simultaneously. The removal process works as follows: In each operation, locate the box with the smallest weight value. Use the forklift to remove that box together with its immediate neighbors on both sides (if available). Repeat this procedure until all boxes have been removed from the warehouse. When multiple boxes share the same minimum weight, the manager chooses the one appearing earliest in the sequence. If a box is at the edge and doesn\'t have neighbors on both sides, only the available adjacent boxes are removed. Calculate the total sum of the minimum-weight boxes selected in each removal operation.',
    examples: [
      {
        input: 'boxes = [5, 4, 1, 3, 2]',
        output: '3',
        explanation: 'Step 1: The smallest weight is 1 (at position 2). Remove boxes at positions 1, 2, and 3 (weights 4, 1, 3). Add 1 to the total. Remaining boxes: [5, 2]. Step 2: The smallest weight is 2 (at position 1). Remove boxes at positions 0 and 1 (weights 5, 2). Add 2 to the total. Final result: 1 + 2 = 3.'
      }
    ],
    constraints: [
      '3 ≤ number of boxes ≤ 2000',
      '1 ≤ box weight ≤ 100,000'
    ],
    boilerplate: {
      python: `def findTotalWeight(boxes):
    # Write your code here
    pass`,
      javascript: `function findTotalWeight(boxes) {
    // Write your code here
    
}`,
      java: `class Solution {
    public int findTotalWeight(int[] boxes) {
        // Write your code here
        
    }
}`,
      cpp: `class Solution {
public:
    int findTotalWeight(vector<int>& boxes) {
        // Write your code here
        
    }
};`,
      csharp: `public class Solution {
    public int FindTotalWeight(int[] boxes) {
        // Write your code here
        
    }
}`
    },
    testCases: [
      {
        input: 'boxes = [5, 4, 1, 3, 2]',
        output: '3'
      },
      {
        input: 'boxes = [6, 4, 9, 10, 34, 56, 54]',
        output: '68'
      },
      {
        input: 'boxes = [132, 45, 65, 765, 345, 243, 75, 67]',
        output: '1120'
      },
      {
        input: 'boxes = [21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12, 21, 12, 63, 21, 42, 32, 12]',
        output: '309'
      }
    ]
  },
  {
    id: 2,
    title: 'Two Sum',
    difficulty: 'Medium',
    description: 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.',
    examples: [
      {
        input: 'nums = [2,7,11,15], target = 9',
        output: '[0,1]',
        explanation: 'Because nums[0] + nums[1] == 9, we return [0, 1].'
      },
      {
        input: 'nums = [3,2,4], target = 6',
        output: '[1,2]'
      },
      {
        input: 'nums = [3,3], target = 6',
        output: '[0,1]'
      }
    ],
    constraints: [
      '2 <= nums.length <= 10^4',
      '-10^9 <= nums[i] <= 10^9',
      '-10^9 <= target <= 10^9',
      'Only one valid answer exists.'
    ],
    boilerplate: {
      python: `def twoSum(nums, target):
    # Write your code here
    pass`,
      javascript: `function twoSum(nums, target) {
    // Write your code here
    
}`,
      java: `class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Write your code here
        
    }
}`,
      cpp: `class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // Write your code here
        
    }
};`,
      csharp: `public class Solution {
    public int[] TwoSum(int[] nums, int target) {
        // Write your code here
        
    }
}`
    },
    testCases: [
      {
        input: 'nums = [2,7,11,15], target = 9',
        output: '[0,1]'
      },
      {
        input: 'nums = [3,2,4], target = 6',
        output: '[1,2]'
      },
      {
        input: 'nums = [3,3], target = 6',
        output: '[0,1]'
      },
      {
        input: 'nums = [1,5,3,7,2], target = 9',
        output: '[3,4]'
      }
    ]
  },
  {
    id: 3,
    title: 'Reverse Linked List',
    difficulty: 'Easy',
    description: 'Given the head of a singly linked list, reverse the list, and return the reversed list.',
    examples: [
      {
        input: 'head = [1,2,3,4,5]',
        output: '[5,4,3,2,1]'
      },
      {
        input: 'head = [1,2]',
        output: '[2,1]'
      }
    ],
    constraints: [
      'The number of nodes in the list is the range [0, 5000].',
      '-5000 <= Node.val <= 5000'
    ],
    boilerplate: {
      python: `def reverseList(head):
    # Write your code here
    pass`,
      javascript: `function reverseList(head) {
    // Write your code here
    
}`,
      java: `class Solution {
    public ListNode reverseList(ListNode head) {
        // Write your code here
        
    }
}`,
      cpp: `/**
 * Definition for singly-linked list.
 * struct ListNode {
 *     int val;
 *     ListNode *next;
 *     ListNode() : val(0), next(nullptr) {}
 *     ListNode(int x) : val(x), next(nullptr) {}
 *     ListNode(int x, ListNode *next) : val(x), next(next) {}
 * };
 */
class Solution {
public:
    ListNode* reverseList(ListNode* head) {
        // Write your code here
        
    }
};`,
      csharp: `/**
 * Definition for singly-linked list.
 * public class ListNode {
 *     public int val;
 *     public ListNode next;
 *     public ListNode(int val=0, ListNode next=null) {
 *         this.val = val;
 *         this.next = next;
 *     }
 * }
 */
public class Solution {
    public ListNode ReverseList(ListNode head) {
        // Write your code here
        
    }
}`
    },
    testCases: [
      {
        input: 'head = [1,2,3,4,5]',
        output: '[5,4,3,2,1]'
      },
      {
        input: 'head = [1,2]',
        output: '[2,1]'
      }
    ]
  },
  {
    id: 4,
    title: 'Valid Parentheses',
    difficulty: 'Easy',
    description: 'Given a string s containing just the characters \'(\', \')\', \'{\', \'}\', \'[\' and \']\', determine if the input string is valid.',
    examples: [
      {
        input: 's = "()"',
        output: 'true'
      },
      {
        input: 's = "()[]{}"',
        output: 'true'
      },
      {
        input: 's = "(]"',
        output: 'false'
      }
    ],
    constraints: [
      '1 <= s.length <= 10^4',
      's consists of parentheses only \'()[]{}\'.'
    ],
    boilerplate: {
      python: `def isValid(s):
    # Write your code here
    pass`,
      javascript: `function isValid(s) {
    // Write your code here
    
}`,
      java: `class Solution {
    public boolean isValid(String s) {
        // Write your code here
        
    }
}`,
      cpp: `class Solution {
public:
    bool isValid(string s) {
        // Write your code here
        
    }
};`,
      csharp: `public class Solution {
    public bool IsValid(string s) {
        // Write your code here
        
    }
}`
    },
    testCases: [
      {
        input: 's = "()"',
        output: 'true'
      },
      {
        input: 's = "()[]{}"',
        output: 'true'
      },
      {
        input: 's = "(]"',
        output: 'false'
      }
    ]
  },
  {
    id: 5,
    title: 'Maximum Subarray',
    difficulty: 'Medium',
    description: 'Given an integer array nums, find the contiguous subarray (containing at least one number) which has the largest sum and return its sum.',
    examples: [
      {
        input: 'nums = [-2,1,-3,4,-1,2,1,-5,4]',
        output: '6',
        explanation: 'The subarray [4,-1,2,1] has the largest sum 6.'
      },
      {
        input: 'nums = [1]',
        output: '1'
      },
      {
        input: 'nums = [5,4,-1,7,8]',
        output: '23'
      }
    ],
    constraints: [
      '1 <= nums.length <= 10^5',
      '-10^4 <= nums[i] <= 10^4'
    ],
    boilerplate: {
      python: `def maxSubArray(nums):
    # Write your code here
    pass`,
      javascript: `function maxSubArray(nums) {
    // Write your code here
    
}`,
      java: `class Solution {
    public int maxSubArray(int[] nums) {
        // Write your code here
        
    }
}`,
      cpp: `class Solution {
public:
    int maxSubArray(vector<int>& nums) {
        // Write your code here
        
    }
};`,
      csharp: `public class Solution {
    public int MaxSubArray(int[] nums) {
        // Write your code here
        
    }
}`
    },
    testCases: [
      {
        input: 'nums = [-2,1,-3,4,-1,2,1,-5,4]',
        output: '6'
      },
      {
        input: 'nums = [1]',
        output: '1'
      },
      {
        input: 'nums = [5,4,-1,7,8]',
        output: '23'
      }
    ]
  }
];

export const fetchCodingProblems = async (): Promise<CodingProblem[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_CODING_PROBLEMS);
    }, 500);
  });
};

// Code execution API types
export interface CodeExecutionRequest {
  language: string;
  code: string;
  sample_test_cases: Array<{
    id: string;
    input: string;
    expected_output: string;
  }>;
  user_id: string;
  question_id: string;
}

export interface CodeExecutionResponse {
  execution_id: string;
  summary: {
    total_tests: number;
    passed: number;
    failed: number;
    all_passed: boolean;
    pass_percentage: number;
  };
  test_results: Array<{
    test_case_id: string;
    test_case_number: number;
    input: string;
    expected_output: string;
    actual_output: string;
    error: string | null;
    status: string;
    passed: boolean;
    execution_time_ms: number;
    cpu_usage_percent: number;
    memory_usage_bytes: number;
  }>;
  metadata: {
    replica: string;
    execution_time_ms: number;
    cpu_usage_percent: number;
    memory_usage_mb: number;
  };
  timestamp: string;
}

const CODE_EXECUTOR_API_URL = 'https://ai-ta-ra-code-executor2.happypond-428960e8.eastus2.azurecontainerapps.io/run';

/**
 * Fixes Java class name issues
 * Java requires: Public class name must match filename (Main.java)
 * Solution: Remove 'public' keyword from class declaration
 */
export const fixJavaClassName = (code: string): string => {
  // Remove 'public' keyword from class declaration
  // Changes: "public class Result" -> "class Result"
  // Changes: "public class Solution" -> "class Solution"
  // This allows any class name to work with Main.java filename
  return code.replace(/public\s+class\s+(\w+)/g, 'class $1');
};

/**
 * Transforms input format based on language requirements
 * For C++, Java, C#: converts "boxes = [5, 4, 1, 3, 2]" to format expected by code
 * (count on first line, then each number on separate lines)
 */
export const transformInputForLanguage = (input: string, language: string): string => {
  // Languages that expect count + numbers format
  const countBasedLanguages = ['cpp', 'java', 'csharp'];
  
  if (!countBasedLanguages.includes(language.toLowerCase())) {
    // For Python, JavaScript, etc., return as-is
    return input;
  }

  // Try to extract array from input string
  // Pattern: "variable = [1, 2, 3]" or "[1, 2, 3]"
  const arrayMatch = input.match(/\[([^\]]+)\]/);
  if (!arrayMatch) {
    // If no array found, return as-is (might already be in correct format)
    return input;
  }

  // Extract numbers from the array
  const numbersStr = arrayMatch[1];
  const numbers = numbersStr
    .split(',')
    .map(num => num.trim())
    .filter(num => num.length > 0);

  // Format: first line is count, then each number on separate line
  const formattedInput = `${numbers.length}\n${numbers.join('\n')}`;
  return formattedInput;
};

export const runCodeExecution = async (
  request: CodeExecutionRequest
): Promise<CodeExecutionResponse> => {
  // Console log the request being sent to the API
  console.log('Code execution API request:', JSON.stringify(request, null, 2));
  
  const response = await fetch(CODE_EXECUTOR_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to execute code' }));
    throw new Error(error.detail || 'Failed to execute code');
  }

  const data: CodeExecutionResponse = await response.json();
  console.log('Code execution API response:', JSON.stringify(data, null, 2));
  return data;
};


