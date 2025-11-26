import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import { scheduleTest } from '../../api/candidate.api';

const ScheduleInterviewPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get user's timezone abbreviation
  const timezoneAbbr = new Date().toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop() || 'IST';

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
    setSelectedDate(date);
    setSelectedTime(null); // Reset time when date changes
  };

  const handleTimeClick = (time: string) => {
    setSelectedTime(time);
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

      // Get auth token from localStorage
      const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
      if (!token) {
        throw new Error('Authentication token not found. Please login again.');
      }

      // Navigate immediately with the scheduled date
      // Backend will process MCQ generation in background
      navigate('/test/scheduled', {
        state: {
          scheduledDate: scheduledDateTime.toISOString(),
        },
      });

      // Call the API in background (don't await - let it run asynchronously)
      scheduleTest(scheduledDateTime, token).catch((err) => {
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

  // Set initial selected date to today
  useEffect(() => {
    const today = new Date();
    setSelectedDate(today);
    setCurrentMonth(today.getMonth());
    setCurrentYear(today.getFullYear());
  }, []);

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
      <div className="flex-1 flex items-start justify-center p-8 pt-12">
        <div className="w-full max-w-5xl mb-8">
          {/* Main Card */}
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Schedule Your Interview</h1>

            {/* Interview Details - 2 Columns */}
            <div className="mb-6 grid grid-cols-2 gap-6">
              {/* Left Column */}
              <div className="space-y-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span className="text-xs text-gray-600">Candidate</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{user?.name || 'Jane Doe'}</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs text-gray-600">Role</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">Senior Product Designer at Grid Dynamics</p>
                </div>
              </div>
              
              {/* Right Column */}
              <div className="space-y-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs text-gray-600">Interview Type</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">Technical Interview</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs text-gray-600">Duration</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">180 minutes</p>
                </div>
              </div>
            </div>

            {/* Timezone Notice */}
            <div className="mb-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-2">
              <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-yellow-800">
                Times are shown in your local timezone ({timezoneAbbr})
              </span>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            {/* Date and Time Selection - 2 Columns */}
            <div className="mb-6 grid grid-cols-2 gap-6">
              {/* Date Selection */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">1. Select a Date</h2>
                <div className="border border-gray-200 rounded-lg p-4">
                  {/* Calendar Header */}
                  <div className="flex items-center justify-between mb-4">
                    <button
                      onClick={handlePrevMonth}
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                      type="button"
                    >
                      <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                    <h3 className="text-lg font-semibold text-gray-900">
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
                  <div className="grid grid-cols-7 gap-1">
                    {/* Day Headers */}
                    {dayNames.map((day) => (
                      <div key={day} className="text-center text-xs font-semibold text-gray-600 py-2">
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
                      
                      return (
                        <button
                          key={index}
                          onClick={() => isCurrentMonth && handleDateClick(day)}
                          disabled={!isCurrentMonth}
                          className={`
                            py-2 px-1 text-sm rounded-lg transition-colors
                            ${!isCurrentMonth ? 'text-gray-300 cursor-not-allowed' : 'text-gray-900 hover:bg-gray-100'}
                            ${isSelected ? 'bg-gray-200 font-semibold' : ''}
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
                <h2 className="text-lg font-semibold text-gray-900 mb-4">2. Select a Time</h2>
                <div className="border border-gray-200 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <div className="grid grid-cols-2 gap-2">
                    {timeSlots.map((time) => {
                      const isSelected = selectedTime === time;
                      return (
                        <button
                          key={time}
                          onClick={() => handleTimeClick(time)}
                          className={`
                            py-2 px-3 text-sm rounded-lg border transition-colors
                            ${isSelected 
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
            <div className="flex justify-center">
              <button
                onClick={handleConfirmSchedule}
                disabled={!selectedDate || !selectedTime || isLoading}
                className={`
                  py-3 px-8 rounded-lg font-semibold text-base transition-colors
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

