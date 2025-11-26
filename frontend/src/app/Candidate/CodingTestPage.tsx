import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CodingProvider, useCoding } from '../../context/CodingContext';
import { useVideo } from '../../context/VideoContext';
import LanguageTabs from '../../components/CodeEditor/LanguageTabs';
import CodeEditor from '../../components/CodeEditor/CodeEditor';
import TestCaseViewer from '../../components/CodeEditor/TestCaseViewer';
import OutputViewer from '../../components/CodeEditor/OutputViewer';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useCodingSession } from '../../hooks/useCodingSession';
import { useFullscreenWarning } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';

const CodingTestPageContent = () => {
  const { formatTime, timeRemaining, isLoading, currentProblem, runCode, isRunning, problems, code } = useCoding();
  const { videoStream, requestVideoStream } = useVideo();
  const { goToProblem, currentProblemIndex, totalProblems } = useCodingSession();
  const navigate = useNavigate();
  
  // Calculate attempted questions count
  const getAttemptedCount = () => {
    let attempted = 0;
    problems.forEach((problem) => {
      // Check if code has been modified from boilerplate in any language
      const languages: Array<'python' | 'javascript' | 'java'> = ['python', 'javascript', 'java'];
      const hasAttempted = languages.some((lang) => {
        const codeKey = `${problem.id}-${lang}`;
        const currentCode = code[codeKey] || problem.boilerplate[lang];
        return currentCode !== problem.boilerplate[lang];
      });
      if (hasAttempted) {
        attempted++;
      }
    });
    return attempted;
  };
  
  const [activeTab, setActiveTab] = useState<'testcases' | 'output'>('testcases');
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [showSubmitSectionModal, setShowSubmitSectionModal] = useState(false);
  const [leftPanelWidth, setLeftPanelWidth] = useState(50); // Percentage
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Monitor fullscreen exit with 5 second countdown
  const { showViolation, countdown, handleRedirect } = useFullscreenWarning({
    onFinalAttempt: () => {
      // This will be called when time runs out
    },
  });

  // Handle resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !containerRef.current) return;
      
      const containerRect = containerRef.current.getBoundingClientRect();
      const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
      
      // Constrain between 20% and 80%
      const constrainedWidth = Math.max(20, Math.min(80, newWidth));
      setLeftPanelWidth(constrainedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-gray-600">Loading problems...</div>
      </div>
    );
  }


  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0">
      {/* Header */}
      <header className="w-full max-w-full flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200 m-0 flex-shrink-0">
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
      <div ref={containerRef} className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Column - Problem Description */}
        <aside 
          className="flex-shrink-0 bg-white border-r border-gray-200 overflow-y-auto overflow-x-hidden h-full"
          style={{ width: `${leftPanelWidth}%` }}
        >
          <div className="p-6">
            {/* All Questions Heading */}
            <h3 className="text-base font-semibold text-gray-900 mb-4">All Questions</h3>
            
            {/* Question Navigation Bar */}
            <div className="mb-6 flex gap-2">
              {Array.from({ length: totalProblems }).map((_, index) => (
                <button
                  key={index}
                  onClick={() => goToProblem(index)}
                  className={`px-4 py-2 rounded-lg text-base font-medium transition-all ${
                    currentProblemIndex === index
                      ? 'bg-amber-50 border-2 border-yellow-500 text-gray-900 shadow-md'
                      : 'bg-amber-50 border-2 border-yellow-500 text-gray-900'
                  }`}
                >
                  {index + 1}
                </button>
              ))}
            </div>

            {currentProblem && (
              <>
                {/* Title */}
                <div className="mb-4">
                  <h2 className="text-base font-bold text-gray-900">{currentProblem.title}</h2>
                </div>

                {/* Problem Description */}
                <div className="mb-6">
                  <h3 className="text-base font-semibold text-gray-900 mb-2">Problem Description</h3>
                  <p className="text-base text-gray-700 leading-relaxed">{currentProblem.description}</p>
                </div>

                {/* Examples */}
                <div className="mb-6">
                  <h3 className="text-base font-semibold text-gray-900 mb-3">Examples</h3>
                  {currentProblem.examples.map((example, index) => (
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
                    {currentProblem.constraints.map((constraint, index) => (
                      <li key={index} className="flex items-start gap-2 text-base text-gray-700">
                        <span className="text-gray-600">→</span>
                        <span>{constraint}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        </aside>

        {/* Resize Handle */}
        <div
          className="w-1 bg-gray-300 hover:bg-blue-500 cursor-col-resize flex-shrink-0 transition-colors relative z-10"
          onMouseDown={() => setIsResizing(true)}
          style={{ minWidth: '4px' }}
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-0.5 h-8 bg-gray-400"></div>
          </div>
        </div>

        {/* Right Column - Code Editor */}
        <main 
          className="flex-shrink-0 flex flex-col bg-white h-full overflow-hidden"
          style={{ width: `${100 - leftPanelWidth}%` }}
        >
          {/* Language Tabs */}
          <LanguageTabs onSubmitSection={() => setShowSubmitSectionModal(true)} />

          {/* Code Editor */}
          <div className="flex-1 min-h-0 border-b border-gray-200">
            <CodeEditor />
          </div>

          {/* Bottom Panel - Testcases/Output with Action Buttons */}
          <div className="flex-shrink-0 h-64 flex flex-col border-t border-gray-200">
            {/* Tabs and Action Buttons in Same Line */}
            <div className="flex items-center justify-between border-b border-gray-200 bg-white">
              {/* Tabs */}
              <div className="flex">
                <button
                  onClick={() => setActiveTab('testcases')}
                  className={`px-6 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'testcases'
                      ? 'bg-white text-gray-900 border-b-2 border-gray-900'
                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  Testcases
                </button>
                <button
                  onClick={() => setActiveTab('output')}
                  className={`px-6 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'output'
                      ? 'bg-white text-gray-900 border-b-2 border-gray-900'
                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  Output
                </button>
              </div>
              
              {/* Action Buttons */}
              <div className="flex items-center gap-3 px-4">
                <button
                  onClick={runCode}
                  disabled={isRunning}
                  className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                  </svg>
                  Run Code
                </button>
                <button
                  onClick={runCode}
                  disabled={isRunning}
                  className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                  </svg>
                  Run All Testcases
                </button>
                <button
                  onClick={() => setShowSubmitModal(true)}
                  className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg text-sm font-medium hover:bg-yellow-500 transition-colors"
                >
                  Submit Solution
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'testcases' ? <TestCaseViewer /> : <OutputViewer />}
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0">
        <Footer />
      </div>

      {/* Submit Section Modal */}
      {showSubmitSectionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Submit Section</h2>
            <p className="text-gray-600 mb-2">
              You have attempted <span className="font-semibold text-gray-900">{getAttemptedCount()}</span> out of <span className="font-semibold text-gray-900">{totalProblems}</span> questions.
            </p>
            <p className="text-gray-600 mb-6">Do you wish to submit this section?</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowSubmitSectionModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowSubmitSectionModal(false);
                  navigate('/test-overview');
                }}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              >
                Submit Section
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submit Solution Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Submit Solution</h2>
            <p className="text-gray-600 mb-6">Are you sure you want to submit your solution?</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  console.log('Solution submitted');
                  setShowSubmitModal(false);
                }}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Violation Modal */}
      <FullscreenViolationModal
        isOpen={showViolation}
        countdown={countdown}
        onRedirect={handleRedirect}
      />
    </div>
  );
};

const CodingTestPage = () => {
  return (
    <CodingProvider>
      <CodingTestPageContent />
    </CodingProvider>
  );
};

export default CodingTestPage;

