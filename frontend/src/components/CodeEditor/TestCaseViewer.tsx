import { useState, useEffect } from 'react';
import { useCoding } from '../../context/CodingContext';

const TestCaseViewer = () => {
  const { currentProblem, testResults } = useCoding();
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number | null>(null);

  if (!currentProblem) return null;

  // Use question_uuid instead of id
  const questionUuid = currentProblem.question_uuid;
  const results = questionUuid ? (testResults[questionUuid] || []) : [];
  
  // If we have results from backend, use those. Otherwise use testCases from problem
  // Backend results might include hidden test cases, so we show all results
  const displayResults = results.length > 0 ? results : currentProblem.testCases.map((tc, idx) => ({
    testCaseId: `sample_${idx + 1}`,
    input: tc.input,
    expectedOutput: tc.output,
    actualOutput: null,
    passed: null,
    error: null,
  }));

  // Determine if a test case is hidden
  const isHiddenTestCase = (result: typeof displayResults[0], index: number) => {
    // Check if it's marked as hidden in the result
    if (result.input === 'Hidden test case' || result.expectedOutput === 'Hidden') {
      return true;
    }
    // If we have results from backend, check test_case_id
    if (results.length > 0 && result.testCaseId) {
      // Sample test cases have IDs like "sample_1" or start with "sample_"
      // Hidden ones don't have "sample_" prefix or have "hidden_" prefix
      const isSample = result.testCaseId.startsWith('sample_') || 
                       result.testCaseId.match(/^test_case_0\d+$/); // test_case_000, test_case_001, etc.
      return !isSample;
    }
    // If no testCaseId, check if input/expectedOutput are missing (hidden test cases in run_all mode)
    if (results.length > 0) {
      // Hidden test cases don't have input/expected_output in run_all mode
      const hasInput = result.input && result.input !== 'Hidden test case';
      const hasExpectedOutput = result.expectedOutput && result.expectedOutput !== 'Hidden';
      // If both are missing, it's likely a hidden test case
      if (!hasInput && !hasExpectedOutput) {
        return true;
      }
      // Otherwise, check if index is beyond sample test cases count
      const sampleCount = currentProblem.testCases?.length || 0;
      return index >= sampleCount;
    }
    // If no results yet, all from problem.testCases are sample (visible)
    return false;
  };

  // Select first sample test case by default
  useEffect(() => {
    if (selectedTestCaseIndex === null && displayResults.length > 0) {
      const firstSampleIndex = displayResults.findIndex((_, idx) => !isHiddenTestCase(displayResults[idx], idx));
      if (firstSampleIndex !== -1) {
        setSelectedTestCaseIndex(firstSampleIndex);
      }
    }
  }, [displayResults.length, selectedTestCaseIndex]);

  const selectedResult = selectedTestCaseIndex !== null ? displayResults[selectedTestCaseIndex] : null;
  const selectedIsHidden = selectedTestCaseIndex !== null ? isHiddenTestCase(displayResults[selectedTestCaseIndex], selectedTestCaseIndex) : false;
  const selectedHasResult = selectedResult ? (selectedResult.actualOutput !== null || selectedResult.error !== null) : false;
  const selectedPassed = selectedResult?.passed === true;
  const selectedFailed = selectedResult?.passed === false;

  return (
    <div className="h-full w-full flex overflow-hidden">
      {/* Left Panel - Test Case List */}
      <div className="w-1/3 flex-shrink-0 border-r border-gray-200 overflow-y-auto overflow-x-hidden bg-gray-50 h-full">
        <div className="p-2">
          {displayResults.map((result, index) => {
            const passed = result.passed === true;
            const failed = result.passed === false;
            const isHidden = isHiddenTestCase(result, index);
            const isSelected = selectedTestCaseIndex === index;

            return (
              <button
                key={index}
                onClick={() => {
                  if (!isHidden) {
                    setSelectedTestCaseIndex(index);
                  }
                }}
                disabled={isHidden}
                className={`w-full text-left p-3 mb-2 rounded-lg border transition-colors ${
                  isSelected
                    ? 'bg-blue-100 border-blue-300'
                    : isHidden
                    ? 'bg-gray-100 border-gray-200 cursor-not-allowed opacity-60'
                    : 'bg-white border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {passed ? (
                      <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    ) : failed ? (
                      <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                      </svg>
                    )}
                    <span className={`text-sm font-medium ${
                      isSelected ? 'text-blue-900' : isHidden ? 'text-gray-500' : 'text-gray-700'
                    }`}>
                      Test case {index}
                    </span>
                  </div>
                  {isHidden && (
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right Panel - Test Case Details */}
      <div className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden bg-white h-full">
        {selectedResult && !selectedIsHidden ? (
          <div className="p-4">
            {/* Compiler Message */}
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Compiler Message</h3>
              <div className="bg-gray-900 text-green-400 p-3 rounded border border-gray-700 font-mono text-sm">
                {selectedPassed ? 'Success' : selectedFailed ? 'Failed' : 'Pending'}
              </div>
            </div>

            {/* Input */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-900">Input (stdin)</h3>
                <button className="text-xs text-blue-600 hover:text-blue-800">Download</button>
              </div>
              <div className="bg-gray-900 text-gray-100 p-3 rounded border border-gray-700 font-mono text-sm overflow-x-auto">
                <pre className="whitespace-pre-wrap">{selectedResult.input}</pre>
              </div>
            </div>

            {/* Expected Output */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-900">Expected Output</h3>
                <button className="text-xs text-blue-600 hover:text-blue-800">Download</button>
              </div>
              <div className="bg-gray-900 text-gray-100 p-3 rounded border border-gray-700 font-mono text-sm overflow-x-auto">
                <pre className="whitespace-pre-wrap">{selectedResult.expectedOutput}</pre>
              </div>
            </div>

            {/* Your Output - Show if available */}
            {selectedHasResult && selectedResult.actualOutput !== null && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Your Output</h3>
                <div className={`p-3 rounded border font-mono text-sm overflow-x-auto ${
                  selectedPassed 
                    ? 'bg-green-50 text-green-900 border-green-200' 
                    : 'bg-red-50 text-red-900 border-red-200'
                }`}>
                  <pre className="whitespace-pre-wrap">{selectedResult.actualOutput}</pre>
                </div>
              </div>
            )}

            {/* Error Message - Show if error exists */}
            {selectedResult.error && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-red-700 mb-2">Error</h3>
                <div className="bg-red-50 text-red-900 p-3 rounded border border-red-200 font-mono text-sm overflow-x-auto max-h-48 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{selectedResult.error}</pre>
                </div>
              </div>
            )}

            {/* Wrong Answer Message - Show if failed but no error */}
            {selectedFailed && !selectedResult.error && (
              <div className="mb-4">
                <div className="bg-red-100 border border-red-200 rounded px-3 py-2 text-sm text-red-700">
                  <span className="font-medium">Wrong Answer</span>
                  {selectedResult.actualOutput !== null && (
                    <p className="mt-1 text-xs text-red-600">
                      Your output doesn't match the expected output.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            {selectedIsHidden ? (
              <div className="text-center">
                <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                <p className="text-sm">Hidden test cases are not viewable</p>
              </div>
            ) : (
              <p className="text-sm">Select a test case to view details</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TestCaseViewer;
