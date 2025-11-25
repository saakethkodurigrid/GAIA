"""
INCORRECT SOLUTION - Two Sum Problem
This solution has a bug that causes it to fail some test cases:
- Bug 1: Returns indices in wrong order (reversed)
- Bug 2: Doesn't handle negative numbers correctly
Should FAIL some test cases
"""

def twoSum(nums, target):
    """
    Buggy implementation - returns wrong indices order
    Also fails on negative numbers
    """
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            # BUG: Returns indices in WRONG ORDER (reversed)
            return [i, seen[complement]]  # Should be [seen[complement], i]
        # BUG: Doesn't handle negative numbers properly
        if num > 0:  # This condition causes issues with negative numbers
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



