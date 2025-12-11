import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { startTest } from '../../api/candidate.api';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

const TestScheduledPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [timeRemaining, setTimeRemaining] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  });
  const [scheduledDate, setScheduledDate] = useState<Date | null>(null);
  const [formattedDate, setFormattedDate] = useState<string>('');
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // Extract and store candidate_id from URL on mount, restore to URL if missing
  useEffect(() => {
    const candidateIdFromUrl = searchParams.get('candidate_id');
    const storedCandidateId = localStorage.getItem('current_candidate_id');
    
    console.log('=== TestScheduledPage Mounted ===');
    console.log('Current URL:', window.location.href);
    console.log('candidate_id from URL params:', candidateIdFromUrl || 'NOT FOUND');
    console.log('candidate_id from localStorage:', storedCandidateId || 'NOT FOUND');
    
    if (candidateIdFromUrl) {
      // Store candidate_id in localStorage to use throughout the session
      localStorage.setItem('current_candidate_id', candidateIdFromUrl);
      console.log('✓ Stored candidate_id in localStorage:', candidateIdFromUrl);
    } else if (storedCandidateId) {
      // If URL doesn't have candidate_id but localStorage does, restore it to URL
      console.log('⚠ candidate_id missing in URL, restoring from localStorage');
      const newUrl = `/test/scheduled?candidate_id=${storedCandidateId}`;
      window.history.replaceState({}, '', newUrl);
      console.log('✓ Restored URL to:', window.location.href);
    } else {
      console.log('❌ No candidate_id found in URL or localStorage');
      setStartError('Candidate ID not found. Please access this page using the invitation link.');
    }
    console.log('====================================');
  }, [searchParams]);

  // Initialize scheduled date from location state or fetch from user data
  useEffect(() => {
    const scheduledDateFromState = location.state?.scheduledDate;
    
    if (scheduledDateFromState) {
      const date = new Date(scheduledDateFromState);
      setScheduledDate(date);
      
      // Format the date for display
      const formatted = date.toLocaleDateString('en-US', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
      const time = date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
      setFormattedDate(`${formatted} at ${time}`);
    } else {
      // Fallback: try to get from user data or use default
      const defaultDate = new Date();
      defaultDate.setDate(defaultDate.getDate() + 1);
      defaultDate.setHours(14, 0, 0, 0);
      setScheduledDate(defaultDate);
      
      const formatted = defaultDate.toLocaleDateString('en-US', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
      const time = defaultDate.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
      setFormattedDate(`${formatted} at ${time}`);
    }
  }, [location.state]);

  // Countdown timer logic
  useEffect(() => {
    if (!scheduledDate) return;

    const updateTimer = () => {
      const now = new Date();
      const diff = scheduledDate.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeRemaining({ days: 0, hours: 0, minutes: 0, seconds: 0 });
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeRemaining({ days, hours, minutes, seconds });
    };

    // Update immediately
    updateTimer();

    // Update every second
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [scheduledDate]);

  const handleLogout = () => {
    logout();
  };

  const handleStartAssessment = async () => {
    // Get candidate_id from localStorage (which was stored from URL)
    const candidateId = localStorage.getItem('current_candidate_id');
    if (!candidateId) {
      setStartError('Candidate ID not found. Please access this page using the invitation link with candidate_id parameter.');
      return;
    }

    const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
    if (!token) {
      setStartError('Authentication token not found. Please login again.');
      return;
    }

    console.log('=== Starting Test ===');
    console.log('Using candidate_id from localStorage:', candidateId);
    console.log('====================');

    setIsStarting(true);
    setStartError(null);

    // Navigate immediately without waiting for test generation
    navigate('/test/instructions');

    // Start test session in the background (fire-and-forget)
    // This loads questions into Redis but doesn't block navigation
    startTest(candidateId, token, 180) // 180 minutes (3 hours) total duration
      .then(() => {
        console.log('Test started, data loaded to Redis');
      })
      .catch((error) => {
        console.error('Failed to start test in background:', error);
        // Note: We don't show error to user since they've already navigated
        // The next page will handle retrying if needed
      });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] flex flex-col">
      {/* Header */}
      <Header showUserInfo={true} showLogout={true} showTechInterviewLogo={true} user={user} onLogout={handleLogout} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center py-4 pb-8">
        {/* Inner Container - Main Card */}
        <div 
          className="rounded-lg shadow-lg relative border-2"
          style={{
            width: '500px',
            padding: '24px',
            backgroundColor: '#FFFFFF',
            borderColor: '#FCD34D',
          }}
        >
          <div className="flex flex-col items-center">
            {/* Title */}
            <div className="text-center mb-5">
              <h1 className="text-2xl font-bold text-gray-900 mb-1">Test Not Started Yet!</h1>
              <p className="text-sm text-gray-600">Please wait until the scheduled time to begin your test.</p>
            </div>

            {/* Countdown Timer */}
            <div className="w-full mb-4">
              <p className="text-xs text-gray-600 text-center mb-3">Test starts in</p>
              {/* Golden Box for Timer - Narrower */}
              <div className="flex justify-center mb-4">
                <div 
                  className="rounded-lg border-2 p-3 inline-block"
                  style={{ 
                    backgroundColor: '#FFF7E5',
                    borderColor: '#FCD34D'
                  }}
                >
                  <div className="flex items-center justify-center gap-2">
                    {/* Days - Only show if more than 24 hours */}
                    {timeRemaining.days > 0 && (
                      <>
                        <div className="flex flex-col items-center">
                          <span className="text-xl font-bold text-gray-900">
                            {String(timeRemaining.days).padStart(2, '0')}
                          </span>
                          <span className="text-xs text-gray-600 mt-0.5">Days</span>
                        </div>
                        <span className="text-lg font-bold text-gray-900 mb-5">:</span>
                      </>
                    )}

                    {/* Hours */}
                    <div className="flex flex-col items-center">
                      <span className="text-xl font-bold text-gray-900">
                        {String(timeRemaining.hours).padStart(2, '0')}
                      </span>
                      <span className="text-xs text-gray-600 mt-0.5">Hours</span>
                    </div>

                    <span className="text-lg font-bold text-gray-900 mb-5">:</span>

                    {/* Minutes */}
                    <div className="flex flex-col items-center">
                      <span className="text-xl font-bold text-gray-900">
                        {String(timeRemaining.minutes).padStart(2, '0')}
                      </span>
                      <span className="text-xs text-gray-600 mt-0.5">Minutes</span>
                    </div>

                    <span className="text-lg font-bold text-gray-900 mb-5">:</span>

                    {/* Seconds */}
                    <div className="flex flex-col items-center">
                      <span className="text-xl font-bold text-gray-900">
                        {String(timeRemaining.seconds).padStart(2, '0')}
                      </span>
                      <span className="text-xs text-gray-600 mt-0.5">Seconds</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Scheduled Time */}
              <div className="text-center">
                <p className="text-xs text-gray-500 mb-1">Scheduled Time</p>
                <p className="text-sm font-semibold text-gray-900">
                  {formattedDate || 'Loading...'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Important Instructions Section - Separate box below main card */}
        <div 
          className="rounded-lg bg-yellow-50 border border-orange-300 p-3"
          style={{
            width: '500px',
            marginTop: '12px',
            marginBottom: '16px',
          }}
        >
          <div className="flex items-start gap-2">
            <svg 
              className="w-4 h-4 text-orange-500 flex-shrink-0 mt-0.5" 
              fill="currentColor" 
              viewBox="0 0 20 20"
            >
              <path 
                fillRule="evenodd" 
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" 
                clipRule="evenodd" 
              />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-semibold mb-1.5" style={{ color: '#973C00' }}>Important Instructions</h3>
              <ul className="space-y-0.5 text-xs" style={{ color: '#973C00' }}>
                <li className="flex items-start gap-1.5">
                  <span className="mt-0.5" style={{ color: '#973C00' }}>•</span>
                  <span>Please be ready 5 minutes before the scheduled time</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="mt-0.5" style={{ color: '#973C00' }}>•</span>
                  <span>Ensure you have a stable internet connection</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="mt-0.5" style={{ color: '#973C00' }}>•</span>
                  <span>The test will automatically get started at the scheduled time</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {startError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{startError}</p>
          </div>
        )}

        {/* Start Assessment Button */}
        <button
          onClick={handleStartAssessment}
          disabled={isStarting}
          className={`py-3 px-8 rounded-lg font-semibold text-base transition-colors shadow-md ${
            isStarting
              ? 'bg-gray-400 text-gray-700 cursor-not-allowed'
              : 'bg-yellow-400 text-gray-900 hover:bg-yellow-500'
          }`}
        >
          {isStarting ? 'Starting Test...' : 'Start Assessment'}
        </button>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default TestScheduledPage;
