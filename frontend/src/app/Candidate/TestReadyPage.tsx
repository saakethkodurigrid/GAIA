import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

const TestReadyPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Set background color on body
    document.body.style.backgroundColor = '#FFFBF0';
    return () => {
      // Reset on unmount
      document.body.style.backgroundColor = '';
    };
  }, []);

  const handleLogout = () => {
    logout();
  };

  const handleStartAssessment = () => {
    navigate('/test-overview');
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#FFFBF0' }}>
      {/* Header */}
      <Header showUserInfo={true} showLogout={true} showTechInterviewLogo={true} user={user} onLogout={handleLogout} />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden w-full" style={{ backgroundColor: '#FFFBF0' }}>
        {/* Left Panel */}
        <div className="w-96 border-r-2 border-black flex flex-col p-6" style={{ backgroundColor: '#FFFBF0' }}>
          <div className="flex-1 flex flex-col justify-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Gen AI Engineer Interview</h2>
            <div>
              <p className="text-sm text-gray-600 mb-1">Test duration</p>
              <p className="text-base font-semibold text-gray-900">180 mins</p>
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

