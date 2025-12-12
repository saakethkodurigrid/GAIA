import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { SystemDesignProvider, useSystemDesign } from '../../context/SystemDesignContext';
import { useVideo } from '../../context/VideoContext';
import DesignHeader from '../../components/SystemDesign/DesignHeader';
import ExcalidrawCanvas from '../../components/SystemDesign/ExcalidrawCanvas';
import ClarifyingChat from '../../components/SystemDesign/ClarifyingChat';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useFullscreenWarning } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';
import { localStorage as storage } from '../../utils/localStorage';
const SystemDesignPageContent = () => {
  const { problem, isLoading, submitSolution, timeRemaining } = useSystemDesign();
  const { videoStream, requestVideoStream } = useVideo();
  const navigate = useNavigate();

  // Format time helper
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Track section entry time using timer value
  useEffect(() => {
    // Check if section has been submitted
    const SUBMITTED_SECTIONS_KEY = 'submitted_sections';
    const stored = localStorage.getItem(SUBMITTED_SECTIONS_KEY);
    const submitted = stored ? JSON.parse(stored) : { mcq: false, coding: false, systemDesign: false };
    const isSubmitted = submitted.systemDesign === true;
    
    // If section hasn't been submitted, ALWAYS reset timing when entering to ensure accuracy
    // This prevents timing from being started too early (e.g., on initial page load or provider mount)
    if (!isSubmitted) {
      const existingTiming = storage.getSectionTiming('systemDesign');
      // Reset timing if:
      // 1. No timing exists, OR
      // 2. Timing exists but hasn't been completed (durationMinutes is null), OR
      // 3. Timing was started significantly earlier than current time (more than 10 seconds difference)
      //    This handles cases where timing was initialized before user actually entered the section
      const shouldReset = !existingTiming || 
                         existingTiming.durationMinutes === null ||
                         (existingTiming.startTimeRemaining !== null && 
                          existingTiming.startTimeRemaining !== undefined &&
                          (existingTiming.startTimeRemaining - timeRemaining) > 10);
      
      if (shouldReset) {
        // Use current timer value when entering section - this will overwrite any existing timing
        console.log('=== System Design Section Entry ===');
        console.log(`Timer: ${formatTime(timeRemaining)}`);
        console.log('====================================');
        storage.startSectionTiming('systemDesign', timeRemaining);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount - we intentionally don't want to restart timing when timeRemaining changes

  const handleSubmit = async () => {
    // Mark System Design section as submitted in localStorage immediately
    try {
      const SUBMITTED_SECTIONS_KEY = 'submitted_sections';
      const stored = localStorage.getItem(SUBMITTED_SECTIONS_KEY);
      const submitted = stored ? JSON.parse(stored) : { mcq: false, coding: false, systemDesign: false };
      submitted.systemDesign = true;
      localStorage.setItem(SUBMITTED_SECTIONS_KEY, JSON.stringify(submitted));
    } catch (error) {
      console.error('Error marking System Design as submitted:', error);
    }
    
    // End section timing and calculate duration using current timer value
    console.log('=== System Design Section Exit ===');
    console.log(`Timer: ${formatTime(timeRemaining)}`);
    const durationMinutes = storage.endSectionTiming('systemDesign', timeRemaining);
    if (durationMinutes !== null) {
      console.log(`Duration: ${durationMinutes} minutes`);
    }
    console.log('===================================');
    
    // Navigate immediately to test overview without waiting for evaluation
    navigate('/test-overview');
    
    // Submit solution in the background (fire-and-forget)
    submitSolution().catch((error) => {
      console.error('Failed to submit solution:', error);
      // Error is logged but doesn't block navigation
    });
  };
  // Monitor fullscreen exit with 5 second countdown
  const { showViolation, countdown, handleRedirect } = useFullscreenWarning({
    onFinalAttempt: () => {
      // This will be called when time runs out
    },
  });
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-gray-600">Loading problem...</div>
      </div>
    );
  }
  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0">
      {/* Header */}
      <DesignHeader onSubmit={handleSubmit} />
      {/* Main Content */}
      <div className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Panel (70%) */}
        <div className="w-[70%] flex-shrink-0 flex flex-col bg-white border-r border-gray-200 h-full overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Problem Section - Fixed height, scrollable */}
            <div className="flex-shrink-0 p-6 overflow-y-auto border-b border-gray-200 bg-gray-50" style={{ maxHeight: '201px' }}>
              <div className="mb-3">
                <h2 className="text-xl font-bold text-gray-900 mb-0">{problem?.title}</h2>
              </div>
              <div>
                <p className="text-sm text-gray-700 leading-relaxed m-0">{problem?.description}</p>
              </div>
            </div>
            {/* Canvas Container */}
            <div className="flex-1 min-h-0 flex flex-col p-6 overflow-hidden">
              {/* Excalidraw Canvas - Takes all space */}
              <div className="flex-1 min-h-0 w-full">
                <ExcalidrawCanvas />
              </div>
            </div>
          </div>
        </div>
        {/* Right Panel (30%) - Chat */}
        <div className="w-[30%] flex-shrink-0 h-full bg-white border-l border-gray-200">
          <ClarifyingChat />
        </div>
      </div>
      {/* Footer */}
      <div className="flex-shrink-0">
        <Footer />
      </div>
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
const SystemDesignPage = () => {
  return (
    <SystemDesignProvider>
      <SystemDesignPageContent />
    </SystemDesignProvider>
  );
};
export default SystemDesignPage;