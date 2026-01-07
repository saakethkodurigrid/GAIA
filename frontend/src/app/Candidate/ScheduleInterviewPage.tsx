import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import { scheduleTest } from '../../api/candidate.api';
import { localStorage as storage } from '../../utils/localStorage';
import { TEST_DURATION_MINUTES_CONSTANT } from '../../utils/constants';

const ScheduleInterviewPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get user's timezone abbreviation
  const timezoneAbbr = new Date().toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop() || 'IST';

  // Helper function to get minimum allowed date/time (1 hour from now)
  const getMinimumDateTime = useCallback(() => {
    const now = new Date();
    const minDateTime = new Date(now.getTime() + 60 * 60 * 1000); // Add 1 hour
    return minDateTime;
  }, []);

  // Helper function to check if a date is in the past (or less than 1 hour from now)
  const isDateDisabled = (day: number, month: number, year: number) => {
    const minDateTime = getMinimumDateTime();
    const dateOnly = new Date(year, month, day);
    const minDateOnly = new Date(minDateTime.getFullYear(), minDateTime.getMonth(), minDateTime.getDate());
    
    // If date is before minimum date, it's disabled
    if (dateOnly < minDateOnly) {
      return true;
    }
    
    // If date is today or future, we'll check times separately
    return false;
  };

  // Helper function to check if a time slot is valid (at least 1 hour from now)
  const isTimeSlotDisabled = (time: string, selectedDate: Date | null) => {
    if (!selectedDate) return false;
    
    const minDateTime = getMinimumDateTime();
    
    // Parse the time string
    const [timeStr, period] = time.split(' ');
    const [hours, minutes] = timeStr.split(':');
    let hour24 = parseInt(hours, 10);
    
    if (period === 'PM' && hour24 !== 12) {
      hour24 += 12;
    } else if (period === 'AM' && hour24 === 12) {
      hour24 = 0;
    }

    // Create a date with the selected date and time
    const scheduledDateTime = new Date(selectedDate);
    scheduledDateTime.setHours(hour24, parseInt(minutes, 10), 0, 0);

    // Check if the scheduled time is at least 1 hour from now
    return scheduledDateTime < minDateTime;
  };

  // Generate time slots (15-minute intervals from 9:00 AM to 5:00 PM)
  const generateTimeSlots = () => {
    const slots = [];
    for (let hour = 9; hour < 17; hour++) {
      for (let minute = 0; minute < 60; minute += 15) {
        const time = new Date();
        time.setHours(hour, minute, 0, 0);
        const timeString = time.toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: true 
        });
        slots.push(timeString);
      }
    }
    return slots;
  };

  const timeSlots = generateTimeSlots();

  // Calendar functions
  const getDaysInMonth = (month: number, year: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (month: number, year: number) => {
    return new Date(year, month, 1).getDay();
  };

  const handlePrevMonth = () => {
    const minDateTime = getMinimumDateTime();
    const minMonth = minDateTime.getMonth();
    const minYear = minDateTime.getFullYear();
    
    // Don't allow navigation to past months
    if (currentYear < minYear || (currentYear === minYear && currentMonth <= minMonth)) {
      return;
    }
    
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  const handleDateClick = (day: number) => {
    const date = new Date(currentYear, currentMonth, day);
    const minDateTime = getMinimumDateTime();
    const dateOnly = new Date(currentYear, currentMonth, day);
    const minDateOnly = new Date(minDateTime.getFullYear(), minDateTime.getMonth(), minDateTime.getDate());
    
    // Prevent selecting past dates
    if (dateOnly < minDateOnly) {
      setError('Cannot select a date in the past');
      return;
    }
    
    setSelectedDate(date);
    setSelectedTime(null); // Reset time when date changes
    setError(null); // Clear any previous errors
  };

  const handleTimeClick = (time: string) => {
    if (!selectedDate) {
      setError('Please select a date first');
      return;
    }
    
    // Check if this time slot is disabled
    if (isTimeSlotDisabled(time, selectedDate)) {
      setError('Selected time must be at least 1 hour from now');
      return;
    }
    
    setSelectedTime(time);
    setError(null); // Clear any previous errors
  };

  const handleConfirmSchedule = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    if (!selectedDate || !selectedTime) {
      setError('Please select both date and time');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Parse the selected time and combine with selected date
      const [time, period] = selectedTime.split(' ');
      const [hours, minutes] = time.split(':');
      let hour24 = parseInt(hours, 10);
      
      if (period === 'PM' && hour24 !== 12) {
        hour24 += 12;
      } else if (period === 'AM' && hour24 === 12) {
        hour24 = 0;
      }

      // Create a new date with the selected date and time
      const scheduledDateTime = new Date(selectedDate);
      scheduledDateTime.setHours(hour24, parseInt(minutes, 10), 0, 0);

      // Final validation: ensure scheduled time is at least 1 hour from now
      const minDateTime = getMinimumDateTime();
      if (scheduledDateTime < minDateTime) {
        setError('Selected date and time must be at least 1 hour from now');
        setIsLoading(false);
        return;
      }

      // Get candidate ID from localStorage (which was stored from URL)
      const candidateId = localStorage.getItem('current_candidate_id');
      if (!candidateId) {
        throw new Error('Candidate ID not found. Please access this page using the invitation link with candidate_id parameter.');
      }

      // Get auth token from localStorage
      const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
      
      // Debug logging for token and candidate_id
      console.log('=== Schedule Test Request ===');
      console.log('auth_token:', localStorage.getItem('auth_token') ? 'Present' : 'Missing');
      console.log('google_id_token:', localStorage.getItem('google_id_token') ? 'Present' : 'Missing');
      console.log('Token being used:', token ? `${token.substring(0, 20)}...` : 'No token found');
      console.log('Candidate ID (from localStorage):', candidateId);
      console.log('===========================');
      
      if (!token) {
        throw new Error('Authentication token not found. Please login again.');
      }

      // Convert to IST format for navigation state
      // Extract date components and format with IST offset (+05:30)
      const toISTString = (date: Date): string => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}+05:30`;
      };

      // Log what we're sending to backend
      console.log('=== Scheduling Interview - Data Being Sent ===');
      console.log('Selected Date:', selectedDate);
      console.log('Selected Time:', selectedTime);
      console.log('Parsed hour24:', hour24);
      console.log('Parsed minutes:', parseInt(minutes, 10));
      console.log('scheduledDateTime (Date object):', scheduledDateTime);
      console.log('scheduledDateTime ISO string:', scheduledDateTime.toISOString());
      console.log('scheduledDateTime Local string:', scheduledDateTime.toString());
      console.log('scheduledDateTime Local time:', scheduledDateTime.toLocaleString());
      console.log('IST formatted string:', toISTString(scheduledDateTime));
      console.log('==============================================');

      // Navigate to confirmation page with the scheduled date
      // Backend will process MCQ generation in background
      navigate('/interview/confirmed', {
        state: {
          scheduledDate: toISTString(scheduledDateTime),
        },
      });

      // Call the API in background (don't await - let it run asynchronously)
      scheduleTest(scheduledDateTime, token, candidateId).catch((err) => {
        // Log error but don't block navigation
        console.error('Background schedule test error:', err);
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to schedule test. Please try again.';
      setError(errorMessage);
      console.error('Schedule test error:', err);
      setIsLoading(false);
    }
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const dayNames = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

  const daysInMonth = getDaysInMonth(currentMonth, currentYear);
  const firstDay = getFirstDayOfMonth(currentMonth, currentYear);
  const days = [];

  // Add days from previous month
  const prevMonthDays = getDaysInMonth(currentMonth - 1 < 0 ? 11 : currentMonth - 1, currentMonth - 1 < 0 ? currentYear - 1 : currentYear);
  for (let i = firstDay - 1; i >= 0; i--) {
    days.push({ day: prevMonthDays - i, isCurrentMonth: false });
  }

  // Add days from current month
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({ day: i, isCurrentMonth: true });
  }

  // Add days from next month to fill the grid
  const totalCells = days.length;
  const remainingCells = 42 - totalCells; // 6 rows * 7 days
  for (let i = 1; i <= remainingCells; i++) {
    days.push({ day: i, isCurrentMonth: false });
  }

  const handleLogout = () => {
    logout();
  };

  // Extract and store candidate_id from URL on mount, restore to URL if missing
  useEffect(() => {
    const candidateIdFromUrl = searchParams.get('candidate_id');
    const storedCandidateId = localStorage.getItem('current_candidate_id');
    
    console.log('=== ScheduleInterviewPage Mounted ===');
    console.log('Current URL:', window.location.href);
    console.log('candidate_id from URL params:', candidateIdFromUrl || 'NOT FOUND');
    console.log('candidate_id from localStorage:', storedCandidateId || 'NOT FOUND');
    
    // Log user data from auth response
    const userDataStr = localStorage.getItem('user_data');
    let userStatus: string | null = null;
    if (userDataStr) {
      try {
        const userData = JSON.parse(userDataStr);
        console.log('=== User Data from Auth Response ===');
        console.log('Full User Data:', JSON.stringify(userData, null, 2));
        console.log('Candidate Name:', userData.name || 'NOT FOUND');
        console.log('Job Role:', userData.jobRole || 'NOT FOUND');
        console.log('Email:', userData.email || 'NOT FOUND');
        console.log('User Type:', userData.userType || 'NOT FOUND');
        console.log('Status:', userData.status || 'NOT FOUND');
        console.log('Candidate ID:', userData.candidateId || 'NOT FOUND');
        console.log('===================================');
        userStatus = userData.status || null;
      } catch (err) {
        console.error('Error parsing user_data:', err);
      }
    } else {
      console.log('⚠ No user_data found in localStorage');
    }
    
    // Check if user status is "completed" - redirect to completed page
    if (userStatus === 'completed') {
      console.log('✓ User status is "completed", redirecting to completed page');
      navigate('/test/completed', { replace: true });
      return;
    }
    
    // Check if user status is "scheduled" - redirect to confirmation page
    if (userStatus === 'scheduled') {
      console.log('✓ User status is "scheduled", redirecting to confirmation page');
      navigate('/interview/confirmed', { replace: true });
      return;
    }
    
    if (candidateIdFromUrl) {
      // Check if candidate_id has changed and flush test data if needed
      storage.checkAndFlushOnCandidateChange(candidateIdFromUrl);
      // Store candidate_id in localStorage to use throughout the session
      localStorage.setItem('current_candidate_id', candidateIdFromUrl);
      console.log('✓ Stored candidate_id in localStorage:', candidateIdFromUrl);
    } else if (storedCandidateId) {
      // If URL doesn't have candidate_id but localStorage does, restore it to URL
      console.log('⚠ candidate_id missing in URL, restoring from localStorage');
      const newUrl = `/schedule?candidate_id=${storedCandidateId}`;
      window.history.replaceState({}, '', newUrl);
      console.log('✓ Restored URL to:', window.location.href);
    } else {
      console.log('❌ No candidate_id found in URL or localStorage');
      setError('Candidate ID not found. Please access this page using the invitation link.');
    }
    console.log('====================================');
  }, [searchParams, navigate]);

  // Set initial selected date to today (or minimum allowed date)
  useEffect(() => {
    const minDateTime = getMinimumDateTime();
    const today = new Date();
    const minDateOnly = new Date(minDateTime.getFullYear(), minDateTime.getMonth(), minDateTime.getDate());
    const todayDateOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    
    // Set to today if it's valid, otherwise set to minimum date
    const initialDate = todayDateOnly >= minDateOnly ? today : minDateTime;
    setSelectedDate(initialDate);
    setCurrentMonth(initialDate.getMonth());
    setCurrentYear(initialDate.getFullYear());
  }, [getMinimumDateTime]);

  // Log user data when it's available
  useEffect(() => {
    if (user) {
      console.log(user);
      console.log('=== User Data from Auth Context ===');
      console.log('Candidate Name:', user.name);
      console.log('Job Role:', user.jobRole);
      console.log('Email:', user.email);
      console.log('User Type:', user.userType);
      console.log('Status:', user.status);
      console.log('Candidate ID:', user.candidateId);
      console.log('Full User Object:', JSON.stringify(user, null, 2));
      console.log('===================================');
    }
  }, [user]);

  // Redirect if already scheduled
//   useEffect(() => {
//     if (user?.status === 'scheduled') {
//       navigate('/test/scheduled', { replace: true });
//     }
//   }, [user?.status, navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] flex flex-col">
      {/* Header */}
      <Header 
        showUserInfo={true} 
        showLogout={true} 
        showTechInterviewLogo={true} 
        user={user} 
        onLogout={handleLogout} 
      />

      {/* Main Content */}
      <div className="flex-1 flex items-start justify-center p-4 pt-6">
        <div className="w-full max-w-5xl mb-4">
          {/* Main Card */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h1 className="text-xl font-bold text-gray-900 mb-4">Schedule Your Interview</h1>

            {/* Interview Details - 2 Columns */}
            <div className="mb-3 grid grid-cols-2 gap-4">
              {/* Left Column */}
              <div className="space-y-4">
                <div className="py-1">
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span className="text-xs text-gray-600">Candidate</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{user?.name || 'Jane Doe'}</p>
                </div>
                <div className="py-1">
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs text-gray-600">Role</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{user?.jobRole || 'Senior Backend Developer'}</p>
                </div>
              </div>
              
              {/* Right Column */}
              <div className="space-y-4">
                <div className="py-1">
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs text-gray-600">Interview Type</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">Technical Interview</p>
                </div>
                <div className="py-1">
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs text-gray-600">Duration</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{TEST_DURATION_MINUTES_CONSTANT} minutes</p>
                </div>
              </div>
            </div>

            {/* Timezone Notice */}
            <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-2">
              <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs text-yellow-800">
                Times are shown in your local timezone ({timezoneAbbr})
              </span>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-xs text-red-800">{error}</p>
              </div>
            )}

            {/* Date and Time Selection - 2 Columns */}
            <div className="mb-4 grid grid-cols-2 gap-4">
              {/* Date Selection */}
              <div>
                <h2 className="text-base font-semibold text-gray-900 mb-2">1. Select a Date</h2>
                <div className="border border-gray-200 rounded-lg p-3 h-[420px] flex flex-col">
                  {/* Calendar Header */}
                  <div className="flex items-center justify-between mb-2 flex-shrink-0">
                    {(() => {
                      const minDateTime = getMinimumDateTime();
                      const minMonth = minDateTime.getMonth();
                      const minYear = minDateTime.getFullYear();
                      const isPrevDisabled = currentYear <= minYear && currentMonth <= minMonth;
                      
                      return (
                        <button
                          onClick={handlePrevMonth}
                          disabled={isPrevDisabled}
                          className={`p-2 rounded-lg transition-colors ${
                            isPrevDisabled 
                              ? 'opacity-50 cursor-not-allowed' 
                              : 'hover:bg-gray-100'
                          }`}
                          type="button"
                        >
                          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                          </svg>
                        </button>
                      );
                    })()}
                    <h3 className="text-sm font-semibold text-gray-900">
                      {monthNames[currentMonth]} {currentYear}
                    </h3>
                    <button
                      onClick={handleNextMonth}
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                      type="button"
                    >
                      <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>

                  {/* Calendar Grid */}
                  <div className="grid grid-cols-7 gap-1 flex-1">
                    {/* Day Headers */}
                    {dayNames.map((day) => (
                      <div key={day} className="text-center text-xs font-semibold text-gray-600 py-1">
                        {day}
                      </div>
                    ))}
                    
                    {/* Calendar Days */}
                    {days.map(({ day, isCurrentMonth }, index) => {
                      const isSelected = selectedDate && 
                        isCurrentMonth && 
                        day === selectedDate.getDate() &&
                        currentMonth === selectedDate.getMonth() &&
                        currentYear === selectedDate.getFullYear();
                      
                      const isDisabled = !isCurrentMonth || isDateDisabled(day, currentMonth, currentYear);
                      
                      return (
                        <button
                          key={index}
                          onClick={() => isCurrentMonth && !isDateDisabled(day, currentMonth, currentYear) && handleDateClick(day)}
                          disabled={isDisabled}
                          className={`
                            py-1 px-1 text-xs rounded transition-colors
                            ${isDisabled ? 'text-gray-300 cursor-not-allowed opacity-50' : 'text-gray-900 hover:bg-gray-100'}
                            ${isSelected && !isDisabled ? 'bg-gray-200 font-semibold' : ''}
                          `}
                          type="button"
                        >
                          {day}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Time Selection */}
              <div>
                <h2 className="text-base font-semibold text-gray-900 mb-2">2. Select a Time</h2>
                <div className="border border-gray-200 rounded-lg p-3 h-[420px] overflow-y-auto">
                  <div className="grid grid-cols-2 gap-1.5">
                    {timeSlots.map((time) => {
                      const isSelected = selectedTime === time;
                      const isDisabled = isTimeSlotDisabled(time, selectedDate);
                      return (
                        <button
                          key={time}
                          onClick={() => !isDisabled && handleTimeClick(time)}
                          disabled={isDisabled}
                          className={`
                            py-1.5 px-2 text-xs rounded border transition-colors
                            ${isDisabled 
                              ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed opacity-50' 
                              : isSelected 
                                ? 'bg-blue-50 border-blue-500 text-blue-700 font-semibold' 
                                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                            }
                          `}
                          type="button"
                        >
                          {time}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Confirm Button */}
            <div className="flex justify-center mt-4">
              <button
                onClick={handleConfirmSchedule}
                disabled={!selectedDate || !selectedTime || isLoading}
                className={`
                  py-2.5 px-6 rounded-lg font-semibold text-sm transition-colors
                  ${selectedDate && selectedTime && !isLoading
                    ? 'bg-gray-700 text-white hover:bg-gray-800 cursor-pointer'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
                type="button"
              >
                {isLoading ? 'Scheduling...' : 'Confirm Schedule'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default ScheduleInterviewPage;

