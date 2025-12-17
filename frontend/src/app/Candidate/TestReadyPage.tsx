import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import { localStorage as storage } from '../../utils/localStorage';
import { clearFullscreenExitCount } from '../../hooks/useFullscreenWarning';
import { startTest } from '../../api/candidate.api';

const TestReadyPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Set background color on body
    document.body.style.backgroundColor = '#FFFBF0';
    
    // Clear any existing timer when landing on TestReadyPage
    // Timer should only start when user clicks "Start Assessment"
    console.log('TestReadyPage mounted - ensuring timer is cleared and timer_started flag is removed...');
    storage.clearTimer();
    window.localStorage.removeItem('timer_just_initialized');
    window.localStorage.removeItem('timer_initialized_at');
    window.localStorage.removeItem('timer_started'); // Remove flag to prevent any timer operations
    console.log('Timer cleared and timer_started flag removed. Timer will only start when user clicks "Start Assessment".');
    
    return () => {
      // Reset on unmount
      document.body.style.backgroundColor = '';
    };
  }, []);

  const handleLogout = () => {
    logout();
  };

  const handleStartAssessment = () => {
    // Get candidate_id and token for backend call (will be used in background)
    const candidateId = user?.candidateId || localStorage.getItem('current_candidate_id');
    const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
    
    if (!candidateId) {
      console.error('Candidate ID not found');
      alert('Error: Candidate ID not found. Please login again.');
      return;
    }
    
    if (!token) {
      console.error('Authentication token not found');
      alert('Error: Authentication token not found. Please login again.');
      return;
    }

    // Always reset timer to 180 minutes when user clicks "Start Assessment"
    // Clear any existing timer first
    console.log('User clicked Start Assessment - Initializing fresh timer...');
    storage.clearTimer();
    
    // Clear section timings first for new test session
    console.log('Clearing section timings for new test session...');
    storage.clearAllSectionTimings();
    console.log('Section timings reset to 0. Starting fresh test session.');
    
    // Set flag to allow timer initialization/syncing - THIS IS THE ONLY PLACE THIS FLAG IS SET
    window.localStorage.setItem('timer_started', 'true');
    console.log('Timer started flag set to true - timer operations are now allowed');
    
    // Initialize frontend timer to 180 minutes (10800 seconds) - timer starts NOW
    // This happens immediately for instant UI response
    console.log('Initializing timer to 180 minutes (10800 seconds) starting now...');
    storage.setTimerEndTime(10800); // 180 minutes = 10800 seconds, timer starts counting down immediately
    console.log('Timer initialized: Starting with 10800 seconds (180 minutes) at', new Date().toISOString());
    
    // Reset violation counts for new test session
    console.log('Resetting violation counts for new test session...');
    clearFullscreenExitCount();
    window.localStorage.removeItem('fullscreenWarning');
    window.localStorage.removeItem('cheating_detection_events');
    console.log('Violation counts reset to 0. Starting fresh test session.');
    
    // Set a flag and timestamp to indicate timer was just initialized (so TestOverviewPage doesn't override it)
    window.localStorage.setItem('timer_just_initialized', 'true');
    window.localStorage.setItem('timer_initialized_at', Date.now().toString());
    
    // Navigate IMMEDIATELY to test overview page (don't wait for backend)
    console.log('Navigating to test overview page immediately...');
    navigate('/test-overview');
    
    // Start backend test session in the background (fire-and-forget)
    // This will sync with frontend timer when TestOverviewPage loads
    console.log('Starting backend test session in background...');
    startTest(candidateId, token, 180) // 180 minutes (3 hours) total duration
      .then((startResponse) => {
        console.log('Backend test session started:', startResponse);
        
        // If backend returns remaining_seconds, update localStorage
        // TestOverviewPage will sync with this when it loads
        if (startResponse.remaining_seconds !== undefined && startResponse.remaining_seconds > 0) {
          console.log('Backend timer initialized:', startResponse.remaining_seconds, 'seconds');
          // Update localStorage - TestOverviewPage will pick this up on sync
          storage.setTimerEndTime(startResponse.remaining_seconds);
        }
      })
      .catch((error) => {
        console.error('Failed to start backend test session (background):', error);
        // Frontend timer is already running, so user experience is not affected
        // TestOverviewPage will continue using frontend timer
      });
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#FFFBF0' }}>
      {/* Header */}
      <Header showUserInfo={true} showLogout={true} showTechInterviewLogo={true} user={user} onLogout={handleLogout} />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden w-full" style={{ backgroundColor: '#FFFBF0' }}>
        {/* Left Panel */}
        <div className="w-96 border-r-2 border-black flex flex-col p-6" style={{ backgroundColor: '#FFFBF0' }}>
          <div className="flex-1 flex flex-col justify-center items-center text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">{user?.jobRole || 'Technical'} Interview</h2>
            <div>
              <p className="text-lg font-bold text-gray-600 mb-1">Test duration</p>
              <p className="text-xl font-bold text-gray-900">180 mins</p>
            </div>
          </div>
        </div>

        {/* Right Panel - Ready Message */}
        <div className="flex-1 flex flex-col justify-center items-center overflow-y-auto p-8" style={{ backgroundColor: '#FFFBF0' }}>
          <div className="text-center">
            <p className="text-gray-700 mb-4">
              You have now completed familiarizing with the platform
            </p>
            <h1 className="text-3xl font-bold text-gray-900 mb-8">
              Click here to start the technical assessment.
            </h1>

            <button
              onClick={handleStartAssessment}
              className="bg-yellow-400 text-gray-900 py-3 px-8 rounded-lg font-semibold text-base hover:bg-yellow-500 transition-colors shadow-md"
            >
              Start Assessment
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default TestReadyPage;

