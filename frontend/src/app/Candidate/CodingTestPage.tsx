import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CodingProvider, useCoding } from '../../context/CodingContext';
import LanguageTabs from '../../components/CodeEditor/LanguageTabs';
import CodeEditor from '../../components/CodeEditor/CodeEditor';
import TestCaseViewer from '../../components/CodeEditor/TestCaseViewer';
import OutputViewer from '../../components/CodeEditor/OutputViewer';
import Footer from '../../components/Footer';
import Toast from '../../components/Toast';
import ConfirmationModal from '../../components/ConfirmationModal';
import { useCodingSession } from '../../hooks/useCodingSession';
import { localStorage as storage } from '../../utils/localStorage';
import { finalizeCodingSection } from '../../api/coding.api';
import { useAuth } from '../../context/AuthContext';
import { useFullscreenWarning } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';
import ConnectionStatus from '../../components/ConnectionStatus';

const CodingTestPageContent = () => {
  const { formatTime, timeRemaining, isLoading, currentProblem, runCode, runAllTestCases, isRunning, problems, code, submitAnswer, submittedQuestions, findNextUnsubmittedQuestion } = useCoding();
  const { goToProblem, currentProblemIndex, totalProblems } = useCodingSession();
  const { user } = useAuth();
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

  // Handle instant submit solution
  const handleSubmitSolution = () => {
    const isCurrentQuestionSubmitted = !!(currentProblem?.question_uuid && submittedQuestions?.has(currentProblem.question_uuid));
    
    if (isCurrentQuestionSubmitted) {
      return;
    }
    
    if (submitAnswer && currentProblem?.question_uuid) {
      // Call submit (fires in background, returns immediately)
      submitAnswer();
      
      // Show success toast
      setToastMessage('Question submitted successfully!');
      setShowToast(true);
      
      // Check if all questions will be submitted (including current one)
      const willBeAllSubmitted = problems.every(problem => {
        if (!problem?.question_uuid) return false;
        if (problem.question_uuid === currentProblem.question_uuid) {
          return true; // Current question will be submitted
        }
        return submittedQuestions?.has(problem.question_uuid);
      });
      
      if (willBeAllSubmitted) {
        // All questions will be submitted - show submit section modal after toast
        pendingNavigationRef.current = { nextIndex: null, showSectionModal: true };
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
        
        // Store navigation info to execute after toast
        pendingNavigationRef.current = { nextIndex, showSectionModal: false };
      }
    }
  };
  
  const [activeTab, setActiveTab] = useState<'testcases' | 'output'>('testcases');
  const [showSubmitSectionModal, setShowSubmitSectionModal] = useState(false);
  const [leftPanelWidth, setLeftPanelWidth] = useState(50); // Percentage
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const pendingNavigationRef = useRef<{ nextIndex: number | null; showSectionModal: boolean } | null>(null);

  // Monitor fullscreen exit with 5 second countdown
  const { showViolation, countdown, handleRedirect } = useFullscreenWarning({
    onFinalAttempt: () => {
      // This will be called when time runs out
    },
  });

  // Track section entry time using timer value
  useEffect(() => {
    // Check if section has been submitted
    const SUBMITTED_SECTIONS_KEY = 'submitted_sections';
    const stored = localStorage.getItem(SUBMITTED_SECTIONS_KEY);
    const submitted = stored ? JSON.parse(stored) : { mcq: false, coding: false, systemDesign: false };
    const isSubmitted = submitted.coding === true;
    
    // If section hasn't been submitted, ALWAYS reset timing when entering to ensure accuracy
    // This prevents timing from being started too early (e.g., on initial page load or provider mount)
    if (!isSubmitted) {
      const existingTiming = storage.getSectionTiming('coding');
      // Always reset timing if section hasn't been submitted and timing hasn't been completed
      // Also reset if existing timing was started significantly earlier (more than 30 seconds difference)
      // This handles cases where timing was initialized before user actually entered the section
      let shouldReset = !existingTiming || existingTiming.durationMinutes === null;
      
      if (existingTiming && existingTiming.startTimeRemaining !== null && existingTiming.startTimeRemaining !== undefined) {
        const timeDiff = existingTiming.startTimeRemaining - timeRemaining;
        // If timing was started more than 30 seconds ago (relative to current timer), reset it
        if (timeDiff > 30) {
          console.log(`Coding timing was started too early - Previous start: ${formatTime(existingTiming.startTimeRemaining)}, Current: ${formatTime(timeRemaining)}, Diff: ${Math.round(timeDiff / 60 * 100) / 100} minutes - RESETTING`);
          shouldReset = true;
        } else if (shouldReset) {
          console.log(`Resetting Coding timing - Previous start: ${formatTime(existingTiming.startTimeRemaining)}, Current: ${formatTime(timeRemaining)}, Diff: ${Math.round(timeDiff / 60 * 100) / 100} minutes`);
        }
      }
      
      if (shouldReset) {
        // Use current timer value when entering section - this will overwrite any existing timing
        console.log('=== Coding Section Entry ===');
        console.log(`Timer: ${formatTime(timeRemaining)}`);
        console.log('============================');
        storage.startSectionTiming('coding', timeRemaining);
      } else {
        console.log('=== Coding Section Entry (timing already completed) ===');
        console.log(`Timer: ${formatTime(timeRemaining)}`);
        console.log('========================================================');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount - we intentionally don't want to restart timing when timeRemaining changes

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
      {/* Connection Status Indicator */}
      <ConnectionStatus />
      
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
            {/* Question Navigation Bar */}
            <div className="mb-6 flex gap-2">
              {Array.from({ length: totalProblems }).map((_, index) => {
                const problem = problems[index];
                const isSubmitted = !!(problem?.question_uuid && submittedQuestions?.has(problem.question_uuid));
                const isCurrent = currentProblemIndex === index;
                
                return (
                  <button
                    key={index}
                    onClick={() => goToProblem(index)}
                    disabled={isSubmitted}
                    className={`px-4 py-2 rounded-lg text-base font-medium transition-all ${
                      isSubmitted
                        ? 'bg-green-50 border-2 border-green-500 text-gray-900 cursor-not-allowed opacity-75'
                        : isCurrent
                        ? 'bg-blue-50 border-4 border-blue-600 text-gray-900 shadow-lg ring-2 ring-blue-300 font-bold'
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
                {/* Question Heading */}
                <h3 className="text-base font-semibold text-gray-900 mb-4">Question</h3>
                
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
                  <h3 className="text-base font-semibold text-gray-900 mb-3">Question</h3>
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
                        onClick={handleSubmitSolution}
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

      {/* Toast Notification */}
      <Toast
        message={toastMessage}
        type="success"
        isVisible={showToast}
        onClose={() => {
          setShowToast(false);
          // Execute pending navigation after toast closes
          if (pendingNavigationRef.current) {
            const { nextIndex, showSectionModal } = pendingNavigationRef.current;
            if (showSectionModal) {
              setShowSubmitSectionModal(true);
            } else if (nextIndex !== null && nextIndex !== undefined) {
              goToProblem(nextIndex);
            }
            pendingNavigationRef.current = null;
          }
        }}
        duration={1000}
      />

      {/* Submit Section Modal */}
      <ConfirmationModal
        isOpen={showSubmitSectionModal}
        onClose={() => setShowSubmitSectionModal(false)}
        onConfirm={() => {
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
          
          // End section timing and calculate duration using current timer value
          console.log('=== Coding Section Exit ===');
          console.log(`Timer: ${formatTime(timeRemaining)}`);
          const durationSeconds = storage.endSectionTiming('coding', timeRemaining);
          if (durationSeconds !== null) {
            const durationMinutes = Math.round((durationSeconds / 60) * 100) / 100;
            console.log(`Duration: ${durationMinutes} minutes`);
          }
          console.log('===========================');
          
          // Call API to finalize coding section and generate analysis (fire-and-forget)
          console.log('Finalizing coding section...');
          finalizeCodingSection(user?.candidateId)
            .then((response) => {
              console.log('✅ Coding section finalized successfully:', response);
              console.log('Coding Analysis:', response.coding_analysis);
            })
            .catch((error) => {
              console.error('⚠️ Error finalizing coding section:', error);
              // Don't block navigation on error - analysis will be attempted during test completion
            });
          
          // Navigate immediately without waiting for API response
          setShowSubmitSectionModal(false);
          navigate('/test-overview');
        }}
        title="Submit Section"
        message={(() => {
          const submittedCount = problems.filter(p => 
            p?.question_uuid && submittedQuestions?.has(p.question_uuid)
          ).length;
          const allSubmitted = submittedCount === totalProblems;
          
          if (allSubmitted) {
            return `You have submitted all ${totalProblems} questions. Do you wish to submit this section?`;
          }
          return `You have attempted ${getAttemptedCount()} out of ${totalProblems} questions. Do you wish to submit this section?`;
        })()}
        confirmButtonText="Submit"
        confirmButtonColor="yellow"
      />

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

