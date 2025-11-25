"""
CORRECT SOLUTION - Two Sum Problem
This solution uses a hash map for O(n) time complexity
Should pass ALL test cases
"""

def twoSum(nums, target):
    """
    Correct implementation using hash map
    Time: O(n), Space: O(n)
    """
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

if __name__ == '__main__':
    # Read input
    nums = list(map(int, input().split(',')))
    target = int(input())
    
    # Solve
    result = twoSum(nums, target)
    
    # Output in expected format
    print(result)



