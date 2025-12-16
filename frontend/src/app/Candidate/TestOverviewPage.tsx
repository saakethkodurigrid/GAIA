import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useVideo } from '../../context/VideoContext';
import { useCheatingDetectionContext } from '../../context/CheatingDetectionContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useFullscreenWarning, getFullscreenExitCount, clearFullscreenExitCount } from '../../hooks/useFullscreenWarning';
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

// Helper function to calculate and format duration from section timing
// Calculates duration by subtracting end time from start time (both in seconds)
const formatSectionDuration = (sectionName: 'mcq' | 'coding' | 'systemDesign'): string => {
  const timing = storage.getSectionTiming(sectionName);
  
  // Check if section was attempted
  if (!timing || timing.startTimeRemaining === null || timing.startTimeRemaining === undefined) {
    return 'Not attempted';
  }
  
  // Calculate duration in seconds
  let durationSeconds: number;
  
  if (timing.endTimeRemaining !== null && timing.endTimeRemaining !== undefined) {
    // Section was completed: duration = startTimeRemaining - endTimeRemaining
    durationSeconds = timing.startTimeRemaining - timing.endTimeRemaining;
  } else {
    // Section is still active: use current time remaining
    const currentTimeRemaining = storage.getRemainingTime();
    if (currentTimeRemaining === null) {
      return 'Not attempted';
    }
    durationSeconds = timing.startTimeRemaining - currentTimeRemaining;
  }
  
  // Ensure non-negative
  if (durationSeconds < 0) {
    return 'Not attempted';
  }
  
  // Convert seconds to minutes and seconds
  const minutes = Math.floor(durationSeconds / 60);
  const seconds = Math.round(durationSeconds % 60);
  
  // Format as "X min Y sec"
  if (minutes === 0 && seconds === 0) {
    return '0 sec';
  } else if (minutes === 0) {
    return `${seconds} sec`;
  } else if (seconds === 0) {
    return `${minutes} min`;
  } else {
    return `${minutes} min ${seconds} sec`;
  }
};

// Helper function to format duration from seconds to "X min Y sec"
const formatDurationFromSeconds = (durationSeconds: number | null | undefined): string => {
  if (durationSeconds === null || durationSeconds === undefined || durationSeconds < 0) {
    return 'Not attempted';
  }
  
  const totalSeconds = Math.round(durationSeconds);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  if (minutes === 0 && seconds === 0) {
    return '0 sec';
  } else if (minutes === 0) {
    return `${seconds} sec`;
  } else if (seconds === 0) {
    return `${minutes} min`;
  } else {
    return `${minutes} min ${seconds} sec`;
  }
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

  // Check if candidate_id has changed and flush test data if needed
  useEffect(() => {
    if (user?.candidateId) {
      const storedCandidateId = localStorage.getItem('current_candidate_id');
      if (storedCandidateId && storedCandidateId !== user.candidateId) {
        console.log(`[TestOverview] Candidate ID mismatch detected. Flushing test data...`);
        storage.checkAndFlushOnCandidateChange(user.candidateId);
        localStorage.setItem('current_candidate_id', user.candidateId);
      } else if (!storedCandidateId && user.candidateId) {
        // First time storing for this candidate
        localStorage.setItem('current_candidate_id', user.candidateId);
      }
    }
  }, [user?.candidateId]);

  // Initialize timer on first visit to test-overview (180 minutes = 10800 seconds)
  // BUT only if timer wasn't just initialized by TestReadyPage
  useEffect(() => {
    // Check if timer was just initialized by TestReadyPage
    const timerJustInitialized = localStorage.getItem('timer_just_initialized') === 'true';
    const timerInitializedAt = localStorage.getItem('timer_initialized_at');
    const wasRecentlyInitialized = timerInitializedAt && 
      (Date.now() - parseInt(timerInitializedAt, 10)) < 60000; // 60 seconds
    
    if (timerJustInitialized || wasRecentlyInitialized) {
      // Timer was just set by TestReadyPage, use it and remove the flag
      console.log('Timer was just initialized by TestReadyPage, using existing timer...');
      const existingTime = storage.getRemainingTime();
      if (existingTime !== null && existingTime > 0) {
        setTimeRemaining(existingTime);
        setIsTimerInitialized(true);
        console.log('Using timer from TestReadyPage:', existingTime, 'seconds remaining');
      }
      if (timerJustInitialized) {
        localStorage.removeItem('timer_just_initialized');
        localStorage.removeItem('timer_initialized_at');
      }
      return; // Don't override the timer
    }
    
    // Only initialize if timer doesn't exist and wasn't just set
    const existingTime = storage.getRemainingTime();
    if (existingTime === null || existingTime <= 0) {
      // Clear section timings first for new test session
      console.log('Clearing section timings for new test session...');
      storage.clearAllSectionTimings();
      console.log('Section timings reset to 0. Starting fresh test session.');
      
      // Reset timer to 180 minutes for new test session
      console.log('Resetting timer to 180 minutes for new test session...');
      storage.setTimerEndTime(10800); // 180 minutes = 10800 seconds
      setTimeRemaining(10800);
      setIsTimerInitialized(true);
      console.log('Timer initialized: Starting with 10800 seconds (180 minutes)');
      
      // Reset violation counts for new test session
      console.log('Resetting violation counts for new test session...');
      clearFullscreenExitCount();
      localStorage.removeItem('fullscreenWarning');
      localStorage.removeItem('cheating_detection_events');
      console.log('Violation counts reset to 0. Starting fresh test session.');
    } else {
      // Timer exists, use it
      setTimeRemaining(existingTime);
      setIsTimerInitialized(true);
    }
  }, []); // Run once on mount

  // Fetch timer from backend on mount and periodically sync
  useEffect(() => {
    const syncTimer = async () => {
      if (!user?.candidateId) return;

      try {
        const token = window.localStorage.getItem('auth_token') || window.localStorage.getItem('google_id_token');
        if (!token) return;

        // Check if timer was just initialized - if so, don't override with backend
        const timerJustInitialized = localStorage.getItem('timer_just_initialized') === 'true';
        const timerInitializedAt = localStorage.getItem('timer_initialized_at');
        const localTime = storage.getRemainingTime();
        
        // Check if timer was initialized within the last 60 seconds (prevent backend override)
        const wasRecentlyInitialized = timerInitializedAt && 
          (Date.now() - parseInt(timerInitializedAt, 10)) < 60000; // 60 seconds

        const status = await getTestStatus(user.candidateId);
        if (status.success && status.status === 'active' && status.remaining_seconds >= 0) {
          // If timer was just initialized or was initialized recently, don't override with backend time
          // Use the local timer that was just set
          if ((timerJustInitialized || wasRecentlyInitialized) && localTime !== null && localTime > 0) {
            console.log('Timer was just initialized (or initialized recently), keeping local timer:', localTime, 'seconds (not overriding with backend:', status.remaining_seconds, 'seconds)');
            setTimeRemaining(localTime);
            setIsTimerInitialized(true);
            if (timerJustInitialized) {
              localStorage.removeItem('timer_just_initialized');
              localStorage.removeItem('timer_initialized_at');
            }
          } else if (localTime !== null && localTime > 0 && status.remaining_seconds < localTime - 60) {
            // Safeguard: If backend time is significantly less than local time (more than 60 seconds difference),
            // keep the local time to prevent accidental reduction
            // This handles cases where backend might have stale data
            console.log('Backend timer is significantly less than local timer. Keeping local timer:', localTime, 'seconds (backend:', status.remaining_seconds, 'seconds)');
            setTimeRemaining(localTime);
            setIsTimerInitialized(true);
          } else {
            // Normal sync - use backend time
            setTimeRemaining(status.remaining_seconds);
            // Update localStorage with backend time
            storage.setTimerEndTime(status.remaining_seconds);
            setIsTimerInitialized(true);
          }
        } else {
          // If backend doesn't have active timer, check localStorage
          const timerJustInitialized = localStorage.getItem('timer_just_initialized') === 'true';
          const timerInitializedAt = localStorage.getItem('timer_initialized_at');
          const wasRecentlyInitialized = timerInitializedAt && 
            (Date.now() - parseInt(timerInitializedAt, 10)) < 60000; // 60 seconds
          const localTime = storage.getRemainingTime();
          if (localTime !== null && localTime > 0) {
            setTimeRemaining(localTime);
            if (timerJustInitialized) {
              console.log('Using timer from TestReadyPage (backend sync):', localTime, 'seconds remaining');
              localStorage.removeItem('timer_just_initialized');
              localStorage.removeItem('timer_initialized_at');
            }
          } else if (!timerJustInitialized && !wasRecentlyInitialized) {
            // Only initialize if timer doesn't exist AND wasn't just set by TestReadyPage
            console.log('No timer found in backend or localStorage, resetting to 180 minutes...');
            storage.setTimerEndTime(10800);
            setTimeRemaining(10800);
            storage.clearAllSectionTimings();
          }
          setIsTimerInitialized(true);
        }
      } catch (error) {
        console.error('Failed to sync timer from backend:', error);
        // Fallback to localStorage if backend sync fails
        const timerJustInitialized = localStorage.getItem('timer_just_initialized') === 'true';
        const timerInitializedAt = localStorage.getItem('timer_initialized_at');
        const wasRecentlyInitialized = timerInitializedAt && 
          (Date.now() - parseInt(timerInitializedAt, 10)) < 60000; // 60 seconds
        const localTime = storage.getRemainingTime();
        if (localTime !== null && localTime > 0) {
          setTimeRemaining(localTime);
          if (timerJustInitialized) {
            console.log('Using timer from TestReadyPage (error fallback):', localTime, 'seconds remaining');
            localStorage.removeItem('timer_just_initialized');
            localStorage.removeItem('timer_initialized_at');
          }
        } else if (!timerJustInitialized && !wasRecentlyInitialized) {
          // Only initialize if timer doesn't exist AND wasn't just set by TestReadyPage
          console.log('No timer found after sync error, resetting to 180 minutes...');
          storage.setTimerEndTime(10800);
          setTimeRemaining(10800);
          storage.clearAllSectionTimings();
        }
        setIsTimerInitialized(true);
      }
    };

    // First, try to use localStorage immediately for faster UI
    // Check if timer was just initialized by TestReadyPage
    const timerJustInitialized = localStorage.getItem('timer_just_initialized') === 'true';
    const timerInitializedAt = localStorage.getItem('timer_initialized_at');
    const wasRecentlyInitialized = timerInitializedAt && 
      (Date.now() - parseInt(timerInitializedAt, 10)) < 60000; // 60 seconds
    
    const localTime = storage.getRemainingTime();
    if (localTime !== null && localTime > 0) {
      setTimeRemaining(localTime);
      setIsTimerInitialized(true);
      if (timerJustInitialized) {
        console.log('Using timer from TestReadyPage:', localTime, 'seconds remaining');
        localStorage.removeItem('timer_just_initialized');
        localStorage.removeItem('timer_initialized_at');
      }
    } else if (!timerJustInitialized && !wasRecentlyInitialized) {
      // Only initialize if timer doesn't exist AND wasn't just set by TestReadyPage
      // If timer was just initialized, wait for it to be set
      console.log('No timer found in localStorage, resetting to 180 minutes...');
      storage.setTimerEndTime(10800);
      setTimeRemaining(10800);
      storage.clearAllSectionTimings();
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

  // Debug: Log violation counts every 15 seconds
  useEffect(() => {
    const logViolationCounts = () => {
      const cheatingCounts = cheatingDetectionContext.getCheatingEventCounts();
      const fullscreenExitCount = getFullscreenExitCount();
      
      console.log('========================================');
      console.log('🔍 VIOLATION COUNTS (Debug - Every 15s)');
      console.log('========================================');
      console.log(`Tab change: ${cheatingCounts.tabChange}`);
      console.log(`Full screen exits: ${fullscreenExitCount}`);
      console.log('========================================');
    };

    // Log immediately on mount
    logViolationCounts();

    // Set up interval to log every 15 seconds
    const interval = setInterval(logViolationCounts, 15000);

    return () => {
      clearInterval(interval);
    };
  }, [cheatingDetectionContext]);

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
    // Calculate duration from start and end times (in seconds) for accurate results
    console.log('=== Section Timings ===');
    console.log(`MCQ Section: ${formatSectionDuration('mcq')}`);
    console.log(`Coding Section: ${formatSectionDuration('coding')}`);
    console.log(`System Design Section: ${formatSectionDuration('systemDesign')}`);
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
          
          // Get saved answers from localStorage (stored as 1-based indexing)
          const STORAGE_KEY = 'mcq_answers';
          const storedAnswersStr = localStorage.getItem(STORAGE_KEY);
          const storedAnswers: Record<number, number> = storedAnswersStr ? JSON.parse(storedAnswersStr) : {};
          
          // Convert to API format
          // localStorage stores 1-based, so we can use it directly (no need to add 1)
          mcqAnswerItems = mcqQuestions
            .filter((q) => {
              const answer = storedAnswers[q.id];
              return answer !== undefined && answer !== null && q.question_uuid;
            })
            .map((q) => {
              const answer = storedAnswers[q.id];
              return {
                question_uuid: q.question_uuid!,
                candidate_answer: String(answer), // Already 1-based from localStorage: "1", "2", "3", or "4"
              };
            });
          
          console.log('MCQ Answers collected:', mcqAnswerItems.length, 'answers');
        } catch (error) {
          console.warn('Could not fetch MCQ answers:', error);
          // Continue without MCQ answers - backend will fetch from Redis
        }

        // Get sections completed from localStorage
        const submittedSections = getSubmittedSections();

        // Get cheating detection data
        const cheatingCounts = cheatingDetectionContext.getCheatingEventCounts();
        const existingFullScreenExits = getFullscreenExitCount();
        const tabChangeCount = cheatingCounts.tabChange;
        
        // Calculate new fullscreen exit count: existing count minus tab change count
        const fullScreenExits = existingFullScreenExits;
        
        console.log(`[Fullscreen Exit Calculation] Existing count: ${existingFullScreenExits}, Tab changes: ${tabChangeCount}, New count: ${fullScreenExits}`);

        // Convert section timings to backend format - only duration in seconds
        // Calculate duration from start and end times (in seconds) for accuracy
        const convertSectionTimings = () => {
          const timings: { mcq?: number; coding?: number; system_design?: number } = {};
          
          ['mcq', 'coding', 'systemDesign'].forEach((section) => {
            const sectionKey = section === 'systemDesign' ? 'system_design' : section;
            const timing = storage.getSectionTiming(section as 'mcq' | 'coding' | 'systemDesign');
            
            if (!timing || timing.startTimeRemaining === null || timing.startTimeRemaining === undefined) {
              return; // Section not attempted
            }
            
            // Calculate duration in seconds: startTimeRemaining - endTimeRemaining
            let durationSeconds: number;
            
            if (timing.endTimeRemaining !== null && timing.endTimeRemaining !== undefined) {
              // Section was completed: duration = startTimeRemaining - endTimeRemaining
              durationSeconds = timing.startTimeRemaining - timing.endTimeRemaining;
            } else {
              // Section is still active: use current time remaining
              const currentTimeRemaining = storage.getRemainingTime();
              if (currentTimeRemaining === null) {
                return; // Cannot calculate duration
              }
              durationSeconds = timing.startTimeRemaining - currentTimeRemaining;
            }
            
            // Only include if duration is valid and non-negative
            if (durationSeconds >= 0) {
              timings[sectionKey as 'mcq' | 'coding' | 'system_design'] = Math.round(durationSeconds);
            }
          });
          
          return Object.keys(timings).length > 0 ? timings : undefined;
        };

        const sectionTimings = convertSectionTimings();

        // Log section timings before preparing request
        console.log('=== SECTION TIMINGS CONVERSION ===');
        console.log('Raw section timings from localStorage:', {
          mcq: storage.getSectionTiming('mcq'),
          coding: storage.getSectionTiming('coding'),
          systemDesign: storage.getSectionTiming('systemDesign'),
        });
        console.log('Converted section timings (seconds):', sectionTimings);
        if (sectionTimings) {
          console.log('Section timings breakdown:', {
            mcq: sectionTimings.mcq ? formatDurationFromSeconds(sectionTimings.mcq) : 'Not attempted',
            coding: sectionTimings.coding ? formatDurationFromSeconds(sectionTimings.coding) : 'Not attempted',
            system_design: sectionTimings.system_design ? formatDurationFromSeconds(sectionTimings.system_design) : 'Not attempted',
          });
        }
        console.log('===================================');

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
          section_timings: sectionTimings,
          integrity: {
            multiple_face: cheatingCounts.multipleFacesDetected > 0 ? 'yes' as const : 'no' as const,
            full_screen_exits: fullScreenExits,
            tab_change: cheatingCounts.tabChange,
          },
        };

        // Log the complete test request being sent to backend
        console.log('=== COMPLETE TEST REQUEST TO BACKEND ===');
        console.log('Candidate ID:', candidateId);
        console.log('Full Request Body:', JSON.stringify(requestBody, null, 2));
        console.log('Section Timings (being sent):', requestBody.section_timings);
        console.log('MCQ Answers Count:', mcqAnswerItems.length);
        console.log('Sections Completed:', requestBody.sections_completed);
        console.log('Integrity Metrics:', requestBody.integrity);
        console.log(`Fullscreen Violations (full_screen_exits): ${fullScreenExits} (calculated as: ${existingFullScreenExits} - ${tabChangeCount})`);
        console.log('==========================================');

        // Call the complete test API in the background
        const response = await completeTest(requestBody, candidateId);
        
        if (response.success) {
          console.log('Test completed successfully:', response);
          
          // Clear all violation-related localStorage values after successful submission
          console.log('Clearing violation-related localStorage values...');
          clearFullscreenExitCount();
          localStorage.removeItem('fullscreenWarning');
          localStorage.removeItem('cheating_detection_events');
          console.log('Violation data cleared. All values reset to 0/default.');
          
          // Clear section timings and timer after successful test completion
          console.log('Clearing section timings and timer after test completion...');
          storage.clearAllSectionTimings();
          storage.clearTimer();
          console.log('Section timings and timer cleared. All values reset to 0.');
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

