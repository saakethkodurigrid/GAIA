import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

const TestInstructionsPage = () => {
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

  const handleStartTour = () => {
    navigate('/tutorial/mcq');
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
            <p className="text-lg text-gray-600 mb-2">Welcome to your</p>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Gen AI Engineer Interview</h2>
            <div>
              <p className="text-base text-gray-600 mb-1">Test duration</p>
              <p className="text-lg font-semibold text-gray-900">180 mins</p>
            </div>
          </div>
        </div>

        {/* Right Panel - Instructions */}
        <div className="flex-1 flex flex-col justify-center overflow-y-auto p-8 pl-16" style={{ backgroundColor: '#FFFBF0' }}>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Instructions</h1>
            
            <ol className="space-y-4 mb-8 text-lg text-gray-700">
              <li className="flex gap-3">
                <span className="font-semibold text-gray-900 min-w-[24px] flex-shrink-0">1.</span>
                <span className="break-words">Find a quiet and comfortable place where you won't be interrupted.</span>
              </li>
              <li className="flex gap-3">
                <span className="font-semibold text-gray-900 min-w-[24px] flex-shrink-0">2.</span>
                <span className="break-words">
                  You'll begin with a <strong>Guided tour of the platform</strong> to get familiar with the platform — this step is <strong>mandatory</strong>, but your answers won't be saved.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="font-semibold text-gray-900 min-w-[24px] flex-shrink-0">3.</span>
                <span className="break-words">
                  Before starting the sample test, you'll be asked to <strong>upload your photo</strong>, allow <strong>webcam access</strong> for video recording, and <strong>switch to full screen mode</strong>.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="font-semibold text-gray-900 min-w-[24px] flex-shrink-0">4.</span>
                <span className="break-words">
                  The main assessment has three sections – <strong>Multiple Choice Questions, Coding Questions, and System Design</strong> – you can complete them in any order.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="font-semibold text-gray-900 min-w-[24px] flex-shrink-0">5.</span>
                <span className="break-words">
                  You'll have <strong>180 minutes</strong> in total. Once you submit a section, you won't be able to go back to the section and edit the responses.
                </span>
              </li>
            </ol>

            <p className="text-lg text-gray-700 mb-8">
              Take a moment to relax before you begin — this is your space to focus and do your best!
            </p>

            <button
              onClick={handleStartTour}
              className="bg-yellow-400 text-gray-900 py-3 px-8 rounded-lg font-semibold text-base hover:bg-yellow-500 transition-colors shadow-md"
            >
              Start Tour
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default TestInstructionsPage;

