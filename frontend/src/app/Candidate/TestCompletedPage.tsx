import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import type { CheatingEvent } from '../../hooks/useCheatingDetection';

const STORAGE_KEY = 'cheating_detection_events';

const TestCompletedPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Load and log cheating detection events
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const events = JSON.parse(stored) as CheatingEvent[];
        
        console.log('========================================');
        console.log('🔍 CHEATING DETECTION LOGS');
        console.log('========================================');
        console.log(`Total Events Detected: ${events.length}`);
        console.log('');
        
        if (events.length === 0) {
          console.log('✅ No cheating events detected during the test.');
        } else {
          // Group events by type
          const eventsByType = events.reduce((acc, event) => {
            if (!acc[event.type]) {
              acc[event.type] = [];
            }
            acc[event.type].push(event);
            return acc;
          }, {} as Record<string, CheatingEvent[]>);

          // Log summary
          console.log('📊 Event Summary:');
          Object.entries(eventsByType).forEach(([type, typeEvents]) => {
            console.log(`  - ${type}: ${typeEvents.length} occurrence(s)`);
          });
          console.log('');

          // Log detailed events
          console.log('📝 Detailed Events:');
          events.forEach((event, index) => {
            const date = new Date(event.timestamp);
            console.log(`\n[${index + 1}] ${event.type.toUpperCase()}`);
            console.log(`    Timestamp: ${date.toLocaleString()}`);
            console.log(`    Details:`, event.details);
          });
        }
        
        console.log('========================================');
      } else {
        console.log('========================================');
        console.log('🔍 CHEATING DETECTION LOGS');
        console.log('========================================');
        console.log('✅ No cheating events detected during the test.');
        console.log('========================================');
      }
    } catch (error) {
      console.error('Error loading cheating detection events:', error);
    }
  }, []);

  // Prevent back navigation
  useEffect(() => {
    // Replace current history entry to prevent back navigation
    window.history.pushState(null, '', window.location.href);
    
    const handlePopState = () => {
      // If user tries to go back, push the current state again
      window.history.pushState(null, '', window.location.href);
    };

    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const handleLogout = () => {
    logout();
  };

  const handleClose = () => {
    navigate('/auth/login');
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
      <div className="flex-1 flex flex-col items-center justify-center py-8 pb-8">
        {/* Success Icon */}
        <div className="mb-6">
          <div className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center shadow-lg">
            <svg 
              className="w-12 h-12 text-white" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={3} 
                d="M5 13l4 4L19 7" 
              />
            </svg>
          </div>
        </div>

        {/* Main Card */}
        <div 
          className="bg-white rounded-2xl shadow-lg border-t-4 relative"
          style={{
            width: '700px',
            padding: '40px',
            borderTopColor: '#FCD34D',
          }}
        >
          {/* Title */}
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-blue-900 mb-4">
              ✨ Interview Completed!
            </h1>
            <p className="text-base text-gray-700">
              Thank you for completing your technical assessment, <span className="font-semibold">{user?.name || 'Alex'}</span>. We appreciate the time and effort you put into this.
            </p>
          </div>

          {/* What Happens Next Section */}
          <div className="bg-purple-50 rounded-xl p-6 mb-6 border border-purple-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                <svg 
                  className="w-6 h-6 text-white" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" 
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-purple-900 mb-4">What Happens Next?</h2>
                <ul className="space-y-3 text-purple-800">
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 mt-1">•</span>
                    <span>
                      Keep an eye on your inbox (and spam folder) at <span className="font-bold">{user?.email || 'alex.j@email.com'}</span> for updates on your application status.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 mt-1">•</span>
                    <span>
                      Our team is reviewing your assessment, and you'll receive detailed feedback soon.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-500 mt-1">•</span>
                    <span>
                      Expect to hear from HR within <span className="font-bold">3-5 business days</span> if you're selected for the next interview stage.
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Need Help Section */}
          <div className="text-center mb-6">
            <p className="text-sm text-gray-600">
              Need help? If you have any questions or concerns, please reach out to our support team at{' '}
              <a 
                href="mailto:support@company.com" 
                className="text-blue-600 font-semibold hover:text-blue-800 underline"
              >
                support@company.com
              </a>
            </p>
          </div>

          {/* Close Button */}
          <div className="flex justify-center">
            <button
              onClick={handleClose}
              className="bg-gray-700 text-white py-3 px-8 rounded-lg font-semibold text-base hover:bg-gray-800 transition-colors shadow-md"
            >
              Close
            </button>
          </div>
        </div>

        {/* Footer Message */}
        <div className="mt-8 text-center">
          <p className="text-lg text-gray-700">
            Best of luck! We're excited about the possibility of working together. 🚀
          </p>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default TestCompletedPage;

