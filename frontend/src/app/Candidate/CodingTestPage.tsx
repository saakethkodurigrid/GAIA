import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CodingProvider, useCoding } from '../../context/CodingContext';
import LanguageTabs from '../../components/CodeEditor/LanguageTabs';
import CodeEditor from '../../components/CodeEditor/CodeEditor';
import TestCaseViewer from '../../components/CodeEditor/TestCaseViewer';
import OutputViewer from '../../components/CodeEditor/OutputViewer';
import Footer from '../../components/Footer';
import { useCodingSession } from '../../hooks/useCodingSession';

const CodingTestPageContent = () => {
  const { formatTime, timeRemaining, isLoading, currentProblem, runCode, runAllTestCases, isRunning, problems, code, submitAnswer, submittedQuestions, findNextUnsubmittedQuestion } = useCoding();
  const { goToProblem, currentProblemIndex, totalProblems } = useCodingSession();
  const navigate = useNavigate();
  
  // Calculate attempted questions count
  const getAttemptedCount = () => {
    let attempted = 0;
    problems.forEach((problem) => {
      if (!problem.question_uuid) return;
      // Check if code has been modified from boilerplate in any language
      const languages: Array<'python' | 'javascript' | 'java' | 'cpp' | 'csharp'> = ['python', 'javascript', 'java', 'cpp', 'csharp'];
      const hasAttempted = languages.some((lang) => {
        const codeKey = `${problem.question_uuid}-${lang}`;
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
  const [isFullscreenExited, setIsFullscreenExited] = useState(false);
  const wasFullscreenRef = useRef(false);

  // Monitor fullscreen exit - just disable buttons, no popup
  useEffect(() => {
    const checkFullscreen = (): boolean => {
      const doc = document as Document & {
        webkitFullscreenElement?: Element | null;
        mozFullScreenElement?: Element | null;
        msFullscreenElement?: Element | null;
      };
      return !!(
        document.fullscreenElement ||
        doc.webkitFullscreenElement ||
        doc.mozFullScreenElement ||
        doc.msFullscreenElement
      );
    };

    wasFullscreenRef.current = checkFullscreen();

    const handleFullscreenChange = () => {
      const isFullscreen = checkFullscreen();

      // If user exits fullscreen, disable navigation
      if (wasFullscreenRef.current && !isFullscreen) {
        setIsFullscreenExited(true);
      } else if (!wasFullscreenRef.current && isFullscreen) {
        // User returned to fullscreen - re-enable navigation
        setIsFullscreenExited(false);
      }

      wasFullscreenRef.current = isFullscreen;
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, []);

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
              {Array.from({ length: totalProblems }).map((_, index) => {
                const problem = problems[index];
                const isSubmitted = !!(problem?.question_uuid && submittedQuestions?.has(problem.question_uuid));
                const isCurrent = currentProblemIndex === index;
                const isDisabled = isSubmitted || isFullscreenExited;
                
                return (
                  <button
                    key={index}
                    onClick={() => goToProblem(index)}
                    disabled={isDisabled}
                    className={`px-4 py-2 rounded-lg text-base font-medium transition-all ${
                      isSubmitted
                        ? 'bg-green-50 border-2 border-green-500 text-gray-900 cursor-not-allowed opacity-75'
                        : isFullscreenExited
                        ? 'bg-gray-100 border-2 border-gray-400 text-gray-500 cursor-not-allowed opacity-50'
                        : isCurrent
                        ? 'bg-amber-50 border-2 border-yellow-500 text-gray-900 shadow-md'
                        : 'bg-amber-50 border-2 border-yellow-500 text-gray-900 hover:bg-amber-100'
                    }`}
                  >
                    {index + 1}
                  </button>
                );
              })}
            </div>

            {currentProblem && (
              <>
                {/* Title */}
                <div className="mb-4">
                  <h2 className="text-base font-bold text-gray-900">{currentProblem.title}</h2>
                </div>

                {/* Problem Description */}
                <div className="mb-6">
                  <style>{`
                    .problem-description h3 {
                      font-size: 1rem;
                      font-weight: 600;
                      color: #111827;
                      margin-top: 1rem;
                      margin-bottom: 0.5rem;
                    }
                    .problem-description p {
                      margin-bottom: 0.75rem;
                      line-height: 1.6;
                      color: #374151;
                    }
                    .problem-description code {
                      background-color: #f3f4f6;
                      padding: 0.125rem 0.375rem;
                      border-radius: 0.25rem;
                      font-family: monospace;
                      font-size: 0.875rem;
                      color: #1f2937;
                    }
                    .problem-description ul, .problem-description ol {
                      margin-left: 1.5rem;
                      margin-bottom: 0.75rem;
                    }
                    .problem-description li {
                      margin-bottom: 0.25rem;
                    }
                  `}</style>
                  <div 
                    className="problem-description text-base text-gray-700 leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: currentProblem.description }}
                  />
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

          {/* Code Editor and Testcases Container - 60/40 split */}
          <div className="flex-1 min-h-0 flex flex-col">
            {/* Code Editor Section - 60% */}
            <div className="flex-[0.6] min-h-0 flex flex-col">
              <div className="flex-1 min-h-0 overflow-hidden">
                <CodeEditor />
              </div>
              
              {/* Action Buttons */}
              <div className="flex-shrink-0 flex items-center justify-end gap-3 px-4 py-3 border-t border-gray-200 bg-white">
                {(() => {
                  const isCurrentQuestionSubmitted = !!(currentProblem?.question_uuid && submittedQuestions?.has(currentProblem.question_uuid));
                  return (
                    <>
                      <button
                        onClick={runCode}
                        disabled={isRunning || isCurrentQuestionSubmitted}
                        className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                        </svg>
                        Run Code
                      </button>
                      <button
                        onClick={runAllTestCases}
                        disabled={isRunning || isCurrentQuestionSubmitted}
                        className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-blue-600 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                        </svg>
                        Run All Testcases
                      </button>
                      <button
                        onClick={() => setShowSubmitModal(true)}
                        disabled={isRunning || isCurrentQuestionSubmitted}
                        className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg text-sm font-medium hover:bg-yellow-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Submit Solution
                      </button>
                    </>
                  );
                })()}
              </div>
            </div>

            {/* Testcases/Output Panel - 40% */}
            <div className="flex-[0.4] min-h-0 min-w-0 flex flex-col border-t border-gray-200 overflow-hidden">
              {/* Tabs */}
              <div className="flex-shrink-0 flex items-center border-b border-gray-200 bg-white">
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

              {/* Content - Scrollable, takes remaining space */}
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
                {activeTab === 'testcases' ? <TestCaseViewer /> : <OutputViewer />}
              </div>
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
              {(() => {
                const submittedCount = problems.filter(p => 
                  p?.question_uuid && submittedQuestions?.has(p.question_uuid)
                ).length;
                const allSubmitted = submittedCount === totalProblems;
                
                if (allSubmitted) {
                  return (
                    <>
                      You have submitted all <span className="font-semibold text-gray-900">{totalProblems}</span> questions.
                    </>
                  );
                }
                return (
                  <>
                    You have attempted <span className="font-semibold text-gray-900">{getAttemptedCount()}</span> out of <span className="font-semibold text-gray-900">{totalProblems}</span> questions.
                  </>
                );
              })()}
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
                  // Mark Coding section as submitted in localStorage
                  try {
                    const SUBMITTED_SECTIONS_KEY = 'submitted_sections';
                    const stored = localStorage.getItem(SUBMITTED_SECTIONS_KEY);
                    const submitted = stored ? JSON.parse(stored) : { mcq: false, coding: false, systemDesign: false };
                    submitted.coding = true;
                    localStorage.setItem(SUBMITTED_SECTIONS_KEY, JSON.stringify(submitted));
                  } catch (error) {
                    console.error('Error marking Coding as submitted:', error);
                  }
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
                  const isCurrentQuestionSubmitted = !!(currentProblem?.question_uuid && submittedQuestions?.has(currentProblem.question_uuid));
                  
                  if (isCurrentQuestionSubmitted) {
                    setShowSubmitModal(false);
                    return;
                  }
                  
                  if (submitAnswer && currentProblem?.question_uuid) {
                    // Call submit (fires in background, returns immediately)
                    submitAnswer();
                    setShowSubmitModal(false);
                    
                    // Check if all questions will be submitted (including current one)
                    const willBeAllSubmitted = problems.every(problem => {
                      if (!problem?.question_uuid) return false;
                      if (problem.question_uuid === currentProblem.question_uuid) {
                        return true; // Current question will be submitted
                      }
                      return submittedQuestions?.has(problem.question_uuid);
                    });
                    
                    if (willBeAllSubmitted) {
                      // All questions will be submitted - show submit section modal
                      setShowSubmitSectionModal(true);
                    } else if (findNextUnsubmittedQuestion) {
                      // Find next unsubmitted question (excluding current one which will be submitted)
                      const tempSubmitted = new Set(submittedQuestions);
                      tempSubmitted.add(currentProblem.question_uuid);
                      
                      // Find next unsubmitted question
                      let nextIndex: number | null = null;
                      for (let i = currentProblemIndex + 1; i < problems.length; i++) {
                        const problem = problems[i];
                        if (problem?.question_uuid && !tempSubmitted.has(problem.question_uuid)) {
                          nextIndex = i;
                          break;
                        }
                      }
                      // If no unsubmitted question found after current, search from beginning
                      if (nextIndex === null) {
                        for (let i = 0; i < currentProblemIndex; i++) {
                          const problem = problems[i];
                          if (problem?.question_uuid && !tempSubmitted.has(problem.question_uuid)) {
                            nextIndex = i;
                            break;
                          }
                        }
                      }
                      
                      if (nextIndex !== null && nextIndex !== undefined) {
                        // Navigate to next unsubmitted question
                        goToProblem(nextIndex);
                      }
                    }
                  }
                }}
                disabled={isRunning || !!(currentProblem?.question_uuid && submittedQuestions?.has(currentProblem.question_uuid))}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

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

