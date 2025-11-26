import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { MCQProvider, useMCQ } from '../../context/MCQContext';
import { useVideo } from '../../context/VideoContext';
import ProgressSidebar from '../../components/MCQ/ProgressSidebar';
import QuestionCard from '../../components/MCQ/QuestionCard';
import SubmitSectionModal from '../../components/MCQ/SubmitSectionModal';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useFullscreenWarning } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';

const MCQPageContent = () => {
  const { formatTime, timeRemaining, isLoading, answers, questions, savedAnswers } = useMCQ();
  const { videoStream, requestVideoStream } = useVideo();
  const navigate = useNavigate();
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [hasAutoSubmitted, setHasAutoSubmitted] = useState(false);

  const handleSubmit = useCallback((submittedAnswers: Record<number, number>) => {
    // Format responses: questionId-optionIndex or null
    const responses: Record<string, string | null> = {};
    
    questions.forEach((question) => {
      const answer = submittedAnswers[question.id];
      if (answer !== undefined && answer !== null) {
        responses[`${question.id}-${answer}`] = `${question.id}-${answer}`;
      } else {
        responses[`${question.id}`] = null;
      }
    });
    
    console.log('MCQ Responses:', responses);
    console.log('Detailed Responses:');
    questions.forEach((question) => {
      const answer = submittedAnswers[question.id];
      if (answer !== undefined && answer !== null) {
        console.log(`Question ${question.id}: ${answer}`);
      } else {
        console.log(`Question ${question.id}: null`);
      }
    });
    
    // Close modal and navigate to test overview page
    setShowSubmitModal(false);
    navigate('/test-overview', { replace: true });
  }, [questions, navigate]);

  // Auto-submit when timer reaches zero
  useEffect(() => {
    if (timeRemaining === 0 && !isLoading && !hasAutoSubmitted) {
      setHasAutoSubmitted(true);
      // Use savedAnswers for auto-submit, fallback to answers if not saved
      const finalAnswers = { ...savedAnswers, ...answers };
      handleSubmit(finalAnswers);
    }
  }, [timeRemaining, isLoading, hasAutoSubmitted, savedAnswers, answers, handleSubmit]);

  // Monitor fullscreen exit with 5 second countdown
  const { showViolation, countdown, handleRedirect } = useFullscreenWarning({
    onFinalAttempt: () => {
      // This will be called when time runs out
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-gray-600">Loading questions...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0">
      {/* Header */}
      <header className="w-full max-w-full flex items-center justify-between px-8 py-3 bg-white border-b border-gray-200 m-0 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl text-purple-600">&lt;/&gt;</span>
          <h1 className="text-xl font-semibold text-gray-800">Multiple Choice Assessment</h1>
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border-2 border-green-500 rounded-lg font-semibold text-sm">
            <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-green-600">{formatTime(timeRemaining)}</span>
          </div>
        </div>
      </header>


      {/* Main Content */}
      <div className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Sidebar */}
        <aside className="flex-[0_0_25%] w-1/4 min-w-[280px] bg-white border-r border-gray-200 p-6 overflow-y-auto overflow-x-hidden m-0 h-full">
          <ProgressSidebar />
        </aside>

        {/* Right Main Area */}
        <main className="flex-1 min-w-0 p-8 overflow-y-auto overflow-x-hidden m-0 h-full" style={{ backgroundColor: '#F8F4EE' }}>
          <QuestionCard onShowSubmitModal={() => setShowSubmitModal(true)} />
        </main>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0">
        <Footer />
      </div>

      {/* Submit Modal */}
      <SubmitSectionModal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        onSubmit={handleSubmit}
      />

      {/* Fullscreen Violation Modal */}
      <FullscreenViolationModal
        isOpen={showViolation}
        countdown={countdown}
        onRedirect={handleRedirect}
      />

      {/* Video Preview Component */}
      <VideoPreview 
        videoStream={videoStream} 
        onStreamRequest={requestVideoStream}
      />
    </div>
  );
};

const MCQPage = () => {
  return (
    <MCQProvider>
      <MCQPageContent />
    </MCQProvider>
  );
};

export default MCQPage;
