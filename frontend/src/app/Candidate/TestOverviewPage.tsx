import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useVideo } from '../../context/VideoContext';
import { useCheatingDetectionContext } from '../../context/CheatingDetectionContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useFullscreenWarning, getFullscreenExitCount } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';
import { completeTest, getTestStatus } from '../../api/candidate.api';
import { fetchQuestions } from '../../api/questions.api';
import { localStorage as storage } from '../../utils/localStorage';

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
  const cheatingDetectionContext = useCheatingDetectionContext();
  
  // Initialize timer from localStorage or default
  const getInitialTime = (): number => {
    const stored = storage.getRemainingTime();
    if (stored !== null && stored > 0) {
      return stored;
    }
    return 10800; // 180 minutes (3 hours) in seconds
  };

  const [timeRemaining, setTimeRemaining] = useState(getInitialTime());
  const [submittedSections, setSubmittedSections] = useState(getSubmittedSections());
  const [isTimerInitialized, setIsTimerInitialized] = useState(false);

  // Fetch timer from backend on mount and periodically sync
  useEffect(() => {
    const syncTimer = async () => {
      if (!user?.candidateId) return;

      try {
        const token = window.localStorage.getItem('auth_token') || window.localStorage.getItem('google_id_token');
        if (!token) return;

        const status = await getTestStatus(user.candidateId);
        if (status.success && status.status === 'active' && status.remaining_seconds >= 0) {
          setTimeRemaining(status.remaining_seconds);
          // Update localStorage with backend time
          storage.setTimerEndTime(status.remaining_seconds);
          setIsTimerInitialized(true);
        } else {
          // If backend doesn't have active timer, check localStorage
          const localTime = storage.getRemainingTime();
          if (localTime !== null && localTime > 0) {
            setTimeRemaining(localTime);
          }
          setIsTimerInitialized(true);
        }
      } catch (error) {
        console.error('Failed to sync timer from backend:', error);
        // Fallback to localStorage if backend sync fails
        const localTime = storage.getRemainingTime();
        if (localTime !== null && localTime > 0) {
          setTimeRemaining(localTime);
        }
        setIsTimerInitialized(true);
      }
    };

    // First, try to use localStorage immediately for faster UI
    const localTime = storage.getRemainingTime();
    if (localTime !== null && localTime > 0) {
      setTimeRemaining(localTime);
      setIsTimerInitialized(true);
    }

    // Then sync with backend
    syncTimer();

    // Sync every 30 seconds to account for any drift
    const syncInterval = setInterval(syncTimer, 30000);

    return () => clearInterval(syncInterval);
  }, [user?.candidateId]);

  // Countdown timer logic (only start after initial sync)
  useEffect(() => {
    if (!isTimerInitialized) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        const newTime = prev <= 0 ? 0 : prev - 1;
        // Update localStorage with new remaining time
        if (newTime > 0) {
          storage.setTimerEndTime(newTime);
        } else {
          storage.clearTimer();
        }
        return newTime;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isTimerInitialized]);

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
    // End timings for any active sections (sections that were started but not submitted)
    const endActiveSection = (sectionName: 'mcq' | 'coding' | 'systemDesign'): number | null => {
      const timing = storage.getSectionTiming(sectionName);
      if (!timing || timing.startTimeRemaining === null || timing.startTimeRemaining === undefined) return null;
      
      // If already ended, return the stored duration
      if (timing.durationMinutes !== null) {
        return timing.durationMinutes;
      }
      
      // End the timing using current timer value and return the duration
      return storage.endSectionTiming(sectionName, timeRemaining);
    };
    
    // End all active sections
    endActiveSection('mcq');
    endActiveSection('coding');
    endActiveSection('systemDesign');
    
    // Get all section timings
    const sectionTimings = storage.getAllSectionTimings();
    const mcqMinutes = sectionTimings.mcq;
    const codingMinutes = sectionTimings.coding;
    const systemDesignMinutes = sectionTimings.systemDesign;
    
    // Store in localStorage
    const timingData = {
      mcq: mcqMinutes,
      coding: codingMinutes,
      systemDesign: systemDesignMinutes
    };
    try {
      localStorage.setItem('section_timings_final', JSON.stringify(timingData));
    } catch (error) {
      console.error('Error storing section timings:', error);
    }
    
    // Print section timings to console
    console.log('=== Section Timings ===');
    console.log(`MCQ Section: ${mcqMinutes !== null ? `${mcqMinutes} minutes` : 'Not attempted'}`);
    console.log(`Coding Section: ${codingMinutes !== null ? `${codingMinutes} minutes` : 'Not attempted'}`);
    console.log(`System Design Section: ${systemDesignMinutes !== null ? `${systemDesignMinutes} minutes` : 'Not attempted'}`);
    console.log('=======================');
    
    // Get cheating event counts from context
    const cheatingCounts = cheatingDetectionContext.getCheatingEventCounts();
    
    // Get and print fullscreen exit count
    const fullscreenExitCount = getFullscreenExitCount();
    
    // Print cheating logs
    console.log('=== Cheating Detection Logs ===');
    console.log(`Multiple faces detection: ${cheatingCounts.multipleFacesDetected}`);
    console.log(`Tab change: ${cheatingCounts.tabChange}`);
    console.log(`Exit from full screen: ${fullscreenExitCount}`);
    console.log('================================');

    // Get candidate ID
    if (!user?.candidateId) {
      console.error('Candidate ID not found');
      alert('Error: Candidate ID not found. Please login again.');
      return;
    }

    // Capture candidate ID for use in background task
    const candidateId = user.candidateId;

    // Navigate immediately to test completed page
    navigate('/test/completed', { replace: true });

    // Run API call in the background (fire-and-forget)
    (async () => {
      try {
        // Get MCQ questions and answers if available
        let mcqAnswerItems: Array<{ question_uuid: string; candidate_answer: string }> = [];
        
        try {
          // Fetch MCQ questions
          const mcqQuestions = await fetchQuestions(candidateId);
          
          // Get saved answers from localStorage
          const STORAGE_KEY = 'mcq_answers';
          const storedAnswersStr = localStorage.getItem(STORAGE_KEY);
          const answers: Record<number, number> = storedAnswersStr ? JSON.parse(storedAnswersStr) : {};
          
          // Convert to API format
          mcqAnswerItems = mcqQuestions
            .filter((q) => {
              const answer = answers[q.id];
              return answer !== undefined && answer !== null && q.question_uuid;
            })
            .map((q) => {
              const answer = answers[q.id];
              return {
                question_uuid: q.question_uuid!,
                candidate_answer: String(answer + 1), // Add 1 to convert from 0-based to 1-based: "1", "2", "3", or "4"
              };
            });
          
          console.log('MCQ Answers collected:', mcqAnswerItems.length, 'answers');
        } catch (error) {
          console.warn('Could not fetch MCQ answers:', error);
          // Continue without MCQ answers - backend will fetch from Redis
        }

        // Get sections completed from localStorage
        const submittedSections = getSubmittedSections();

        // Prepare request body
        const requestBody = {
          completion_method: 'manual' as const,
          mcq_answers: mcqAnswerItems.length > 0 ? {
            answers: mcqAnswerItems
          } : undefined,
          sections_completed: {
            mcq: submittedSections.mcq,
            coding: submittedSections.coding,
            system_design: submittedSections.systemDesign,
          },
        };

        // Call the complete test API in the background
        const response = await completeTest(requestBody, candidateId);
        
        if (response.success) {
          console.log('Test completed successfully:', response);
        } else {
          console.error('Test completion failed:', response.message || 'Unknown error');
        }
      } catch (error) {
        console.error('Error completing test (background):', error);
        // Error is logged but doesn't affect user experience since navigation already happened
      }
    })();
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

