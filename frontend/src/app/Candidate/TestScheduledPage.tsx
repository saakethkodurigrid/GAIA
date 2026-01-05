import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getScheduledDate } from '../../api/candidate.api';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import { localStorage as storage } from '../../utils/localStorage';

const TestScheduledPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
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
  const [isLoadingScheduledDate, setIsLoadingScheduledDate] = useState(true);
  const [isTimeReached, setIsTimeReached] = useState(false);
  
  // Check if debug mode is enabled (allows starting test before scheduled time)
  const isDebugMode = import.meta.env.VITE_SKIP_TEST_TIMING === 'true';

  // Extract and store candidate_id from URL on mount, restore to URL if missing
  useEffect(() => {
    const candidateIdFromUrl = searchParams.get('candidate_id');
    const storedCandidateId = localStorage.getItem('current_candidate_id');
    
    console.log('=== TestScheduledPage Mounted ===');
    console.log('Current URL:', window.location.href);
    console.log('candidate_id from URL params:', candidateIdFromUrl || 'NOT FOUND');
    console.log('candidate_id from localStorage:', storedCandidateId || 'NOT FOUND');
    
    if (candidateIdFromUrl) {
      // Check if candidate_id has changed and flush test data if needed
      storage.checkAndFlushOnCandidateChange(candidateIdFromUrl);
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

  // Fetch scheduled date from API based on candidate_id
  useEffect(() => {
    const fetchScheduledDate = async () => {
      const candidateId = localStorage.getItem('current_candidate_id');
      if (!candidateId) {
        setIsLoadingScheduledDate(false);
        return;
      }

      const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
      if (!token) {
        setIsLoadingScheduledDate(false);
        return;
      }

      try {
        setIsLoadingScheduledDate(true);
        console.log('=== Fetching Scheduled Date ===');
        console.log('Candidate ID:', candidateId);
        const response = await getScheduledDate(candidateId, token);
        
        console.log('=== Backend Response ===');
        console.log('Full Response:', JSON.stringify(response, null, 2));
        console.log('Response Success:', response.success);
        console.log('Response Message:', response.message);
        console.log('Scheduled Date String:', response.scheduled_date);
        console.log('Scheduled Date Type:', typeof response.scheduled_date);
        console.log('========================');
        
        if (response.success && response.scheduled_date) {
          // Parse the date string from backend (should be in ISO format with timezone)
          const scheduledDateStr = response.scheduled_date;
          console.log('Parsing scheduled date string:', scheduledDateStr);
          
          // Extract IST time components from the string to display correctly
          // The date string format is: YYYY-MM-DDTHH:mm:ss+05:30 or YYYY-MM-DDTHH:mm:ss
          const match = scheduledDateStr.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
          console.log('Regex Match Result:', match);
          
          if (match) {
            const [, year, month, day, hours, minutes] = match;
            console.log('Extracted Components:', { year, month, day, hours, minutes });
            const monthIndex = parseInt(month, 10) - 1;
            const dayNum = parseInt(day, 10);
            const hoursNum = parseInt(hours, 10);
            
            // Create a date object using IST components for date formatting
            // Note: We use local timezone for date formatting, but extract time directly from IST string
            const istDate = new Date(parseInt(year, 10), monthIndex, dayNum);
            
            // Format the date part
            const formatted = istDate.toLocaleDateString('en-US', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            });
            
            // Format the time directly from IST components (without timezone conversion)
            let hours12 = hoursNum;
            let period = 'AM';
            if (hoursNum === 0) {
              hours12 = 12;
            } else if (hoursNum === 12) {
              hours12 = 12;
              period = 'PM';
            } else if (hoursNum > 12) {
              hours12 = hoursNum - 12;
              period = 'PM';
            }
            const time = `${hours12}:${minutes.padStart(2, '0')} ${period}`;
            
            setFormattedDate(`${formatted} at ${time} IST`);
            console.log('Formatted Date String:', `${formatted} at ${time} IST`);
            
            // Set scheduledDate for countdown timer (parse as UTC to avoid timezone conversion)
            // Parse the ISO string and create a date object that represents the IST time
            const date = new Date(scheduledDateStr);
            console.log('Parsed Date Object:', date);
            console.log('Date ISO String:', date.toISOString());
            console.log('Date Local String:', date.toLocaleString());
            setScheduledDate(date);
          } else {
            // Fallback to regular date parsing if regex fails
            const date = new Date(scheduledDateStr);
            setScheduledDate(date);
            
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
          }
        } else {
          // No scheduled date found, use fallback
          console.log('No scheduled date found in response, using fallback');
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
      } catch (error) {
        console.error('=== Error Fetching Scheduled Date ===');
        console.error('Error:', error);
        console.error('Error Details:', JSON.stringify(error, null, 2));
        console.error('=====================================');
        // Fallback on error
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
      } finally {
        setIsLoadingScheduledDate(false);
        console.log('=== Finished Fetching Scheduled Date ===');
      }
    };

    fetchScheduledDate();
  }, []); // Only run once on mount

  // Countdown timer logic
  useEffect(() => {
    if (!scheduledDate) return;

    const updateTimer = () => {
      const now = new Date();
      const diff = scheduledDate.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeRemaining({ days: 0, hours: 0, minutes: 0, seconds: 0 });
        setIsTimeReached(true);
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeRemaining({ days, hours, minutes, seconds });
      setIsTimeReached(false);
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

    console.log('=== Navigating to Instructions ===');
    console.log('Using candidate_id from localStorage:', candidateId);
    console.log('NOTE: Backend test will NOT start until user clicks "Start Assessment" on TestReadyPage');
    console.log('====================');

    setIsStarting(true);
    setStartError(null);

    // Navigate to instructions page
    // DO NOT call startTest() here - backend timer should only start when user clicks "Start Assessment" on TestReadyPage
    navigate('/test/instructions');
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
                  {isLoadingScheduledDate ? 'Loading...' : (formattedDate || 'Not scheduled')}
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
          disabled={isStarting || (!isDebugMode && !isTimeReached)}
          className={`py-3 px-8 rounded-lg font-semibold text-base transition-colors shadow-md ${
            isStarting || (!isDebugMode && !isTimeReached)
              ? 'bg-gray-400 text-gray-700 cursor-not-allowed'
              : 'bg-yellow-400 text-gray-900 hover:bg-yellow-500'
          }`}
        >
          {isStarting ? 'Starting Test...' : 'Start Assessment'}
        </button>
        
        {/* Debug Mode Indicator */}
        {isDebugMode && (
          <p className="text-xs text-orange-600 mt-2 font-semibold">
            Debug Mode: Time restriction disabled
          </p>
        )}
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default TestScheduledPage;
