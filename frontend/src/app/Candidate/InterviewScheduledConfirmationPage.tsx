import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

const InterviewScheduledConfirmationPage = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [formattedDate, setFormattedDate] = useState<string>('');

  // Initialize scheduled date from location state
  useEffect(() => {
    const scheduledDateFromState = location.state?.scheduledDate;
    
    if (scheduledDateFromState) {
      const date = new Date(scheduledDateFromState);
      
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
    }
  }, [location.state]);

  // Auto-logout after 5 seconds
  useEffect(() => {
    const logoutTimer = setTimeout(() => {
      logout();
    }, 5000);

    // Cleanup timer on unmount
    return () => {
      clearTimeout(logoutTimer);
    };
  }, [logout]);

  const handleLogout = () => {
    logout();
  };

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
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Main Card */}
          <div className="bg-white rounded-lg shadow-lg p-8 text-center border-2 border-yellow-200">
            {/* Success Icon */}
            <div className="mb-6 flex justify-center">
              <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center">
                <svg 
                  className="w-10 h-10 text-yellow-600" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M5 13l4 4L19 7" 
                  />
                </svg>
              </div>
            </div>

            {/* Message */}
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Dear {user?.name || 'Candidate'},
            </h1>
            <p className="text-lg text-gray-700 mb-6">
              your interview is scheduled
            </p>

            {/* Interview Timing */}
            <div className="mb-6 p-4 bg-yellow-50 rounded-lg border-2 border-yellow-200">
              <p className="text-sm text-gray-600 mb-2">Interview Timing</p>
              <p className="text-lg font-semibold text-gray-900">
                {formattedDate || 'Loading...'}
              </p>
            </div>

            {/* Email Notice */}
            <div className="mb-8">
              <p className="text-sm text-gray-600 font-bold">
                Please check your email for further information.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default InterviewScheduledConfirmationPage;

