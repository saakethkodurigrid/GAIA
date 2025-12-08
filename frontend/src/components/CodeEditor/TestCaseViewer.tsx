import { useCoding } from '../../context/CodingContext';

const TestCaseViewer = () => {
  const { currentProblem, testResults } = useCoding();

  if (!currentProblem) return null;

  const results = testResults[currentProblem.id] || [];
  const testCases = currentProblem.testCases;

  return (
    <div className="flex flex-col gap-4 p-4">
      {testCases.map((testCase, index) => {
        const result = results[index];
        const status = result?.passed;

        return (
          <div
            key={index}
            className="bg-yellow-50 border border-yellow-200 rounded-lg p-4"
          >
            <div className="mb-2">
              <span className="text-sm font-medium text-gray-700">Input:</span>
              <pre className="mt-1 text-sm text-gray-800 bg-white p-2 rounded border border-gray-200">
                {testCase.input}
              </pre>
            </div>
            {result ? (
              <>
                <div className="mb-2">
                  <span className="text-sm font-medium text-gray-700">Expected Output:</span>
                  <pre className="mt-1 text-sm text-gray-800 bg-white p-2 rounded border border-gray-200">
                    {result.expectedOutput || testCase.output}
                  </pre>
                </div>
                {result.actualOutput !== null && result.actualOutput !== undefined && (
                  <div className="mb-2">
                    <span className="text-sm font-medium text-gray-700">Actual Output:</span>
                    <pre className={`mt-1 text-sm p-2 rounded border ${
                      status === true 
                        ? 'text-green-800 bg-green-50 border-green-200' 
                        : 'text-red-800 bg-red-50 border-red-200'
                    }`}>
                      {result.actualOutput}
                    </pre>
                  </div>
                )}
                <div className="mt-2">
                  <span className={`text-sm font-medium ${
                    status === true ? 'text-green-600' : status === false ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {status === true ? '✓ Passed' : status === false ? '✗ Failed' : 'Pending'}
                  </span>
                </div>
              </>
            ) : (
              <div className="mb-2">
                <span className="text-sm font-medium text-gray-700">Expected Output:</span>
                <pre className="mt-1 text-sm text-gray-800 bg-white p-2 rounded border border-gray-200">
                  {testCase.output}
                </pre>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default TestCaseViewer;

