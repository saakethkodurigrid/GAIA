import { useEffect, useState } from 'react';
import { TourProvider, useTour } from '../../context/TourContext';
import TourOverlay from '../../components/Walkthrough/TourOverlay';
import { mcqTourSteps } from '../../components/Walkthrough/tourGuideSteps';
import Footer from '../../components/Footer';

const TourMCQPageContent = () => {
  const { startTour, isRunning } = useTour();
  const [timeRemaining] = useState(10800); // 3 hours (180 minutes)

  useEffect(() => {
    // Start tour automatically
    startTour(mcqTourSteps);
  }, [startTour]);

  // Note: Navigation to home page is handled by StepTooltip when "Done" is clicked

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Dummy data
  const dummyQuestion = {
    id: 1,
    topic: 'Data Structures',
    question: 'What is the time complexity of binary search in a sorted array?',
    options: [
      'O(n)',
      'O(log n)',
      'O(n log n)',
      'O(1)'
    ]
  };

  const dummyStatuses = {
    answered: 0,
    marked: 0,
    notAnswered: 25
  };

  const totalQuestions = 25;

  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0 relative">
      <TourOverlay />

      {/* Header */}
      <header 
        data-tour="header"
        className="w-full max-w-full flex items-center justify-between px-8 py-3 bg-white border-b border-gray-200 m-0 flex-shrink-0"
        style={{ pointerEvents: isRunning ? 'none' : 'auto' }}
      >
        <div className="flex items-center gap-3">
          <span className="text-xl text-purple-600">&lt;/&gt;</span>
          <h1 className="text-xl font-semibold text-gray-800">Multiple Choice Assessment</h1>
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
        </div>
        <div className="flex items-center gap-4">
          <div 
            data-tour="timer"
            className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border-2 border-green-500 rounded-lg font-semibold text-sm"
          >
            <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-green-600">{formatTime(timeRemaining)}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Sidebar */}
        <aside 
          data-tour="sidebar"
          className="flex-[0_0_25%] w-1/4 min-w-[280px] bg-white border-r border-gray-200 p-6 overflow-y-auto overflow-x-hidden m-0 h-full"
          style={{ pointerEvents: isRunning ? 'none' : 'auto' }}
        >
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-3">
              <h3 className="text-base font-semibold text-gray-800 mb-1">Question Overview</h3>
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3 p-2">
                  <div className="w-6 h-6 rounded bg-green-100 border-2 border-green-500"></div>
                  <span className="flex-1 text-sm text-gray-600">Answered</span>
                  <span className="font-semibold text-gray-800 min-w-6 text-right">{dummyStatuses.answered}</span>
                </div>
                <div className="flex items-center gap-3 p-2">
                  <div className="w-6 h-6 rounded bg-purple-600 border-2 border-purple-600"></div>
                  <span className="flex-1 text-sm text-gray-600">Marked</span>
                  <span className="font-semibold text-gray-800 min-w-6 text-right">{dummyStatuses.marked}</span>
                </div>
                <div className="flex items-center gap-3 p-2">
                  <div className="w-6 h-6 rounded bg-yellow-100 border-2 border-yellow-400"></div>
                  <span className="flex-1 text-sm text-gray-600">Not Answered</span>
                  <span className="font-semibold text-gray-800 min-w-6 text-right">{dummyStatuses.notAnswered}</span>
                </div>
              </div>
            </div>
            
            <div className="flex flex-col gap-3">
              <h3 className="text-base font-semibold text-gray-800 mb-1">All Questions</h3>
              <div className="grid grid-cols-4 gap-2">
                {Array.from({ length: totalQuestions }).map((_, index) => {
                  const isActive = index === 0;
                  
                  let className = 'aspect-square rounded-lg border-2 font-semibold text-sm cursor-pointer flex items-center justify-center relative transition-all hover:scale-105';
                  
                  if (isActive) {
                    className += ' border-amber-700 border-[3px] bg-yellow-100 text-gray-800';
                  } else {
                    className += ' bg-yellow-100 border-yellow-400 text-gray-800';
                  }
                  
                  return (
                    <button
                      key={index}
                      className={className}
                    >
                      <span className="text-sm">{index + 1}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </aside>

        {/* Right Main Area */}
        <main 
          data-tour="question-card"
          className="flex-1 min-w-0 p-8 overflow-y-auto overflow-x-hidden m-0 h-full"
          style={{ backgroundColor: '#F8F4EE', pointerEvents: isRunning ? 'none' : 'auto' }}
        >
          <div className="w-full max-w-full flex flex-col gap-5">
            <div className="flex justify-between items-center w-full">
              <span className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
                {dummyQuestion.topic}
              </span>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600 font-medium">
                  Question 1 of {totalQuestions}
                </span>
                <button
                  data-tour="submit-button"
                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition-colors"
                  disabled={isRunning}
                >
                  Submit Section
                </button>
              </div>
            </div>
            
            <div 
              data-tour="question-text"
              className="text-xl font-semibold text-gray-800 leading-relaxed my-3 w-full break-words"
            >
              {dummyQuestion.question}
            </div>
            
            <div 
              data-tour="options"
              className="flex flex-col gap-3 my-3 w-full"
            >
              {dummyQuestion.options.map((option, index) => {
                const isSelected = index === 1; // O(log n) is selected
                return (
                  <div
                    key={index}
                    className={`flex items-center gap-3 p-4 border-2 rounded-lg bg-white cursor-pointer transition-all w-full ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-400 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-center">
                      <div className={`w-5 h-5 border-2 rounded-full flex items-center justify-center transition-all ${
                        isSelected ? 'border-blue-500' : 'border-gray-400'
                      }`}>
                        {isSelected && (
                          <div className="w-2.5 h-2.5 bg-blue-500 rounded-full"></div>
                        )}
                      </div>
                    </div>
                    <span className="flex-1 text-base text-gray-800">{option}</span>
                  </div>
                );
              })}
            </div>
            
            <div className="flex justify-between items-center gap-4 mt-5 w-full">
              <div className="flex items-center gap-4">
                <button 
                  data-tour="mark-for-review"
                  className="flex items-center gap-2 px-5 py-2 bg-transparent border-2 border-gray-200 rounded-lg text-sm font-medium cursor-pointer transition-all hover:border-gray-400 hover:bg-gray-50 text-gray-800"
                  disabled={isRunning}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                  </svg>
                  Mark for Review
                </button>
                
                <button 
                  className="flex items-center gap-2 px-5 py-2 bg-transparent border-2 border-gray-200 rounded-lg text-sm font-medium cursor-pointer transition-all hover:border-gray-400 hover:bg-gray-50 text-gray-800"
                  disabled={isRunning}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Clear Selection
                </button>
              </div>
              
              <div className="flex items-center gap-4">
                <button
                  className="px-6 py-2 rounded-lg text-sm font-medium bg-gray-100 border-2 border-gray-200 text-gray-400 opacity-50 cursor-not-allowed"
                  disabled={true}
                >
                  Previous
                </button>
                
                <button
                  data-tour="save-next"
                  className="px-6 py-2 bg-yellow-400 text-gray-900 rounded-lg text-sm font-semibold cursor-pointer transition-colors hover:bg-yellow-500"
                  disabled={isRunning}
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0">
        <Footer />
      </div>
    </div>
  );
};

const TourMCQPage = () => {
  return (
    <TourProvider>
      <TourMCQPageContent />
    </TourProvider>
  );
};

export default TourMCQPage;

