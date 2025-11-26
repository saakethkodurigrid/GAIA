import { useEffect, useState } from 'react';
import { TourProvider, useTour } from '../../context/TourContext';
import TourOverlay from '../../components/Walkthrough/TourOverlay';
import { codingTourSteps } from '../../components/Walkthrough/tourGuideSteps';
import Footer from '../../components/Footer';

const TourCodingPageContent = () => {
  const { startTour, isRunning } = useTour();
  const [timeRemaining] = useState(10800); // 3 hours
  const [selectedLanguage, setSelectedLanguage] = useState<'python' | 'javascript' | 'java'>('python');
  const [activeTab, setActiveTab] = useState<'testcases' | 'output'>('testcases');
  const [leftPanelWidth] = useState(50); // Percentage

  useEffect(() => {
    startTour(codingTourSteps);
  }, [startTour]);

  // Note: Navigation to home page is handled by StepTooltip when "Done" is clicked

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const dummyProblem = {
    title: 'Two Sum',
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
    ]
  };

  const totalProblems = 4;

  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0 relative">
      <TourOverlay />

      {/* Header */}
      <header 
        data-tour="header"
        className="w-full max-w-full flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200 m-0 flex-shrink-0"
        style={{ pointerEvents: isRunning ? 'none' : 'auto' }}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl text-purple-600">&lt;/&gt;</span>
          <h1 className="text-2xl font-semibold text-gray-800">Coding Assessment</h1>
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-4 py-2 bg-green-50 border-2 border-green-500 rounded-lg font-semibold text-base">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-green-600">{formatTime(timeRemaining)}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Column - Problem Description */}
        <aside 
          className="flex-shrink-0 bg-white border-r border-gray-200 overflow-y-auto overflow-x-hidden h-full"
          style={{ width: `${leftPanelWidth}%` }}
        >
          <div className="p-6">
            {/* All Questions Heading */}
            <h3 className="text-base font-semibold text-gray-900 mb-4">All Questions</h3>
            
            {/* Question Navigation Bar */}
            <div 
              data-tour="question-nav"
              className="mb-6 flex gap-2"
            >
              {Array.from({ length: totalProblems }).map((_, index) => (
                <button
                  key={index}
                  className={`px-4 py-2 rounded-lg text-base font-medium transition-all ${
                    index === 0
                      ? 'bg-amber-50 border-2 border-yellow-500 text-gray-900 shadow-md'
                      : 'bg-amber-50 border-2 border-yellow-500 text-gray-900'
                  }`}
                  disabled={isRunning}
                >
                  {index + 1}
                </button>
              ))}
            </div>

            <div data-tour="problem-description">
              {/* Title */}
              <div className="mb-4">
                <h2 className="text-base font-bold text-gray-900">{dummyProblem.title}</h2>
              </div>

              {/* Problem Description */}
              <div className="mb-6">
                <h3 className="text-base font-semibold text-gray-900 mb-2">Problem Description</h3>
                <p className="text-base text-gray-700 leading-relaxed">{dummyProblem.description}</p>
              </div>

              {/* Examples */}
              <div className="mb-6">
                <h3 className="text-base font-semibold text-gray-900 mb-3">Examples</h3>
                {dummyProblem.examples.map((example, index) => (
                  <div key={index} className="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="mb-2">
                      <span className="text-base font-medium text-gray-700">Example {index + 1}:</span>
                    </div>
                    <div className="mb-2">
                      <span className="text-base font-medium text-gray-700">Input: </span>
                      <code className="text-base text-gray-800 bg-white px-2 py-1 rounded">{example.input}</code>
                    </div>
                    <div className="mb-2">
                      <span className="text-base font-medium text-gray-700">Output: </span>
                      <code className="text-base text-gray-800 bg-white px-2 py-1 rounded">{example.output}</code>
                    </div>
                    {example.explanation && (
                      <div>
                        <span className="text-base font-medium text-gray-700">Explanation: </span>
                        <span className="text-base text-gray-600">{example.explanation}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Constraints */}
              <div>
                <h3 className="text-base font-semibold text-gray-900 mb-3">Constraints</h3>
                <ul className="list-none space-y-2">
                  {dummyProblem.constraints.map((constraint, index) => (
                    <li key={index} className="flex items-start gap-2 text-base text-gray-700">
                      <span className="text-gray-600">→</span>
                      <span>{constraint}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </aside>

        {/* Right Column - Code Editor */}
        <main 
          className="flex-shrink-0 flex flex-col bg-white h-full overflow-hidden"
          style={{ width: `${100 - leftPanelWidth}%` }}
        >
          {/* Language Tabs */}
          <div 
            data-tour="language-selector"
            className="flex-shrink-0 border-b border-gray-200"
          >
            <div className="flex items-center justify-between px-4 py-2">
              <div className="flex">
                {(['python', 'javascript', 'java'] as const).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => !isRunning && setSelectedLanguage(lang)}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      selectedLanguage === lang
                        ? 'text-gray-900 border-b-2 border-gray-900'
                        : 'text-gray-600 hover:text-gray-800'
                    }`}
                    disabled={isRunning}
                  >
                    {lang.charAt(0).toUpperCase() + lang.slice(1)}
                  </button>
                ))}
              </div>
              <button
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                disabled={isRunning}
              >
                Reset
              </button>
            </div>
          </div>

          {/* Code Editor */}
          <div 
            data-tour="code-editor"
            className="flex-1 min-h-0 border-b border-gray-200"
          >
            <div className="h-full bg-gray-900 text-white p-4 font-mono text-sm overflow-auto">
              <pre className="text-green-400">
{selectedLanguage === 'python' ? `def twoSum(nums, target):
    # Write your code here
    pass` : selectedLanguage === 'javascript' ? `function twoSum(nums, target) {
    // Write your code here
}` : `public int[] twoSum(int[] nums, int target) {
    // Write your code here
}`}
              </pre>
            </div>
          </div>

          {/* Bottom Panel - Testcases/Output with Action Buttons */}
          <div 
            data-tour="test-cases"
            className="flex-shrink-0 h-64 flex flex-col border-t border-gray-200"
          >
            {/* Tabs and Action Buttons in Same Line */}
            <div className="flex items-center justify-between border-b border-gray-200 bg-white">
              {/* Tabs */}
              <div className="flex">
                <button
                  onClick={() => !isRunning && setActiveTab('testcases')}
                  className={`px-6 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'testcases'
                      ? 'bg-white text-gray-900 border-b-2 border-gray-900'
                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
                  disabled={isRunning}
                >
                  Testcases
                </button>
                <button
                  onClick={() => !isRunning && setActiveTab('output')}
                  className={`px-6 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'output'
                      ? 'bg-white text-gray-900 border-b-2 border-gray-900'
                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
                  disabled={isRunning}
                >
                  Output
                </button>
              </div>
              
              {/* Action Buttons */}
              <div className="flex items-center gap-3 px-4">
                <button
                  className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isRunning}
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                  </svg>
                  Run Code
                </button>
                <button
                  className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isRunning}
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                  </svg>
                  Run All Testcases
                </button>
                <button
                  data-tour="submit-solution"
                  className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg text-sm font-medium hover:bg-yellow-500 transition-colors"
                  disabled={isRunning}
                >
                  Submit Solution
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {activeTab === 'testcases' ? (
                <div>
                  <div className="mb-2">
                    <div className="px-3 py-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                      <div className="text-gray-700 mb-1">Input: <code className="text-gray-800">nums = [3,2,4], target = 6</code></div>
                      <div className="text-gray-700">Expected Output: <code className="text-gray-800">[1,2]</code></div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-600">Output will appear here after running code...</div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0">
        <Footer />
      </div>
    </div>
  );
};

const TourCodingPage = () => {
  return (
    <TourProvider>
      <TourCodingPageContent />
    </TourProvider>
  );
};

export default TourCodingPage;

