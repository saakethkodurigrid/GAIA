import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useVideo } from '../../context/VideoContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useFullscreenWarning } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';

// Helper functions for localStorage
const SUBMITTED_SECTIONS_KEY = 'submitted_sections';

const getSubmittedSections = (): { mcq: boolean; coding: boolean; systemDesign: boolean } => {
  try {
    const stored = localStorage.getItem(SUBMITTED_SECTIONS_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Error loading submitted sections from localStorage:', error);
  }
  return { mcq: false, coding: false, systemDesign: false };
};

const TestOverviewPage = () => {
  const { user, logout } = useAuth();
  const { videoStream, requestVideoStream } = useVideo();
  const navigate = useNavigate();
  const [timeRemaining, setTimeRemaining] = useState(3600); // 60 minutes in seconds
  const [submittedSections, setSubmittedSections] = useState(getSubmittedSections());

  // Countdown timer logic
  useEffect(() => {
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 0) return 0;
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Check for submitted sections when component mounts or when navigating back
  useEffect(() => {
    const checkSubmittedSections = () => {
      setSubmittedSections(getSubmittedSections());
    };
    
    checkSubmittedSections();
    // Also check when window gains focus (user might have submitted in another tab)
    window.addEventListener('focus', checkSubmittedSections);
    return () => window.removeEventListener('focus', checkSubmittedSections);
  }, []);

  // Clear any stale fullscreen warning state when landing on overview page
  // This prevents automatic redirect to /test/completed from previous sessions
  useEffect(() => {
    try {
      localStorage.removeItem('fullscreenWarning');
    } catch (error) {
      console.error('Error clearing fullscreen warning state:', error);
    }
  }, []);

  // Monitor fullscreen exit with 5 second countdown
  const { showViolation, countdown, handleRedirect } = useFullscreenWarning({
    onFinalAttempt: () => {
      // This will be called when time runs out
    },
  });

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleLogout = () => {
    logout();
  };

  const handleSolve = (section: string) => {
    // Don't navigate if section is already submitted
    if (section === 'mcq' && submittedSections.mcq) return;
    if (section === 'coding' && submittedSections.coding) return;
    if (section === 'system-design' && submittedSections.systemDesign) return;

    if (section === 'mcq') {
      navigate('/candidate/mcq');
    } else if (section === 'coding') {
      navigate('/candidate/coding');
    } else if (section === 'system-design') {
      navigate('/candidate/system-design');
    }
  };

  const handleSubmitTest = () => {
    // Navigate to test completed page with replace to prevent back navigation
    navigate('/test/completed', { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] relative overflow-y-auto overflow-x-hidden">
      {/* Header */}
      <Header 
        showUserInfo={true} 
        showLogout={true} 
        showTechInterviewLogo={true} 
        showTimer={true}
        timerValue={formatTime(timeRemaining)}
        user={user} 
        onLogout={handleLogout} 
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center py-8 pb-8">
        <div className="max-w-7xl w-full px-4">
          {/* Title and Description */}
          <div className="mb-8">
            <div className="flex justify-center">
              <div className="w-full" style={{ maxWidth: 'calc(3 * 384px + 2 * 2rem)' }}>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Technical Assessment Dashboard</h1>
                <p className="text-base text-gray-700 mb-4">
                  Welcome to your Technical Assessment! This assessment consists of three sections: Multiple Choice, Coding, and System Design.
                </p>
                <p className="text-base text-gray-600 font-bold">
                  Important: Once a section is submitted, you will not be able to revisit or edit your answers.
                </p>
              </div>
            </div>
          </div>

          {/* Cards Container */}
          <div className="flex gap-8 mb-8 justify-center">
            {/* Section 1 - Multiple Choice Question */}
            <div className={`bg-white rounded-xl shadow-lg border-2 p-8 w-96 h-96 flex flex-col justify-center items-center text-center ${
              submittedSections.mcq ? 'border-gray-400 opacity-75' : 'border-gray-200'
            }`}>
              <div className="flex flex-col items-center">
                <p className="text-sm text-gray-500 mb-3">Section 1</p>
                <h2 className="text-2xl font-bold text-gray-900 mb-6 leading-tight">Multiple Choice Question</h2>
                <div className="mb-6">
                  <p className="text-base text-gray-600 mb-2">Total Questions</p>
                  <p className="text-3xl font-bold text-gray-900">25</p>
                </div>
              </div>
              <button
                onClick={() => handleSolve('mcq')}
                disabled={submittedSections.mcq}
                className={`w-full py-3 px-4 rounded-lg font-semibold text-base transition-colors mt-6 ${
                  submittedSections.mcq
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {submittedSections.mcq ? 'Submitted' : 'Solve'}
              </button>
            </div>

            {/* Section 2 - Coding Test */}
            <div className={`bg-white rounded-xl shadow-lg border-2 p-8 w-96 h-96 flex flex-col justify-center items-center text-center ${
              submittedSections.coding ? 'border-gray-400 opacity-75' : 'border-gray-200'
            }`}>
              <div className="flex flex-col items-center">
                <p className="text-sm text-gray-500 mb-3">Section 2</p>
                <h2 className="text-2xl font-bold text-gray-900 mb-6 leading-tight">Coding Test</h2>
                <div className="mb-6">
                  <p className="text-base text-gray-600 mb-2">Total Questions</p>
                  <p className="text-3xl font-bold text-gray-900">4</p>
                </div>
              </div>
              <button
                onClick={() => handleSolve('coding')}
                disabled={submittedSections.coding}
                className={`w-full py-3 px-4 rounded-lg font-semibold text-base transition-colors mt-6 ${
                  submittedSections.coding
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {submittedSections.coding ? 'Submitted' : 'Solve'}
              </button>
            </div>

            {/* Section 3 - System Design */}
            <div className={`bg-white rounded-xl shadow-lg border-2 p-8 w-96 h-96 flex flex-col justify-center items-center text-center ${
              submittedSections.systemDesign ? 'border-gray-400 opacity-75' : 'border-gray-200'
            }`}>
              <div className="flex flex-col items-center">
                <p className="text-sm text-gray-500 mb-3">Section 3</p>
                <h2 className="text-2xl font-bold text-gray-900 mb-6 leading-tight">System Design</h2>
                <div className="mb-6">
                  <p className="text-base text-gray-600 mb-2">Total Questions</p>
                  <p className="text-3xl font-bold text-gray-900">1</p>
                </div>
              </div>
              <button
                onClick={() => handleSolve('system-design')}
                disabled={submittedSections.systemDesign}
                className={`w-full py-3 px-4 rounded-lg font-semibold text-base transition-colors mt-6 ${
                  submittedSections.systemDesign
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {submittedSections.systemDesign ? 'Submitted' : 'Solve'}
              </button>
            </div>
          </div>

          {/* Submit Test Button */}
          <div className="flex justify-center">
            <div className="w-full" style={{ maxWidth: 'calc(3 * 384px + 2 * 2rem)' }}>
              <div className="flex justify-end">
                <button
                  onClick={handleSubmitTest}
                  className="bg-yellow-400 text-gray-900 py-3 px-8 rounded-lg font-semibold text-lg hover:bg-yellow-500 transition-colors shadow-md"
                >
                  Submit Test
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 w-full">
        <Footer />
      </div>

      {/* Fullscreen Violation Modal */}
      <FullscreenViolationModal
        isOpen={showViolation}
        countdown={countdown}
        onRedirect={handleRedirect}
      />

      {/* Video Preview Component */}
      {videoStream && (
        <VideoPreview 
          videoStream={videoStream} 
          onStreamRequest={requestVideoStream}
        />
      )}
    </div>
  );
};

export default TestOverviewPage;

