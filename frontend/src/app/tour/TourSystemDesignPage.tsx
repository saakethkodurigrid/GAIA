import { useEffect, useState } from 'react';
import { TourProvider, useTour } from '../../context/TourContext';
import TourOverlay from '../../components/Walkthrough/TourOverlay';
import { systemDesignTourSteps } from '../../components/Walkthrough/tourGuideSteps';
import { Excalidraw } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';

const TourSystemDesignPageContent = () => {
  const { startTour, isRunning } = useTour();
  const [timeRemaining] = useState(3600);

  useEffect(() => {
    startTour(systemDesignTourSteps);
  }, [startTour]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const dummyProblem = {
    title: 'Design a URL Shortener',
    description: 'Design a service like TinyURL or bit.ly that takes a long URL and returns a shortened URL. The service should handle millions of requests per day and provide analytics on URL usage.'
  };

  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0 relative">
      <TourOverlay />

      {/* Header */}
      <header 
        data-tour="header"
        className="w-full max-w-full flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200 shadow-sm m-0 flex-shrink-0"
        style={{ pointerEvents: isRunning ? 'none' : 'auto' }}
      >
        <button className="flex items-center gap-2 px-4 py-2 bg-transparent border-none cursor-pointer text-base text-gray-800 hover:text-blue-600 transition-colors">
          <span className="text-xl">←</span>
          Back
        </button>
        <div className="flex items-center gap-3 flex-1 justify-center">
          <span className="text-2xl text-gray-600">&lt;/&gt;</span>
          <h1 className="text-2xl font-semibold text-gray-800">System Design Assessment</h1>
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-md font-semibold text-base">
            <span className="text-base">🕐</span>
            <span>{formatTime(timeRemaining)}</span>
          </div>
          <button
            data-tour="submit-button"
            className="px-6 py-2 bg-yellow-400 text-gray-800 rounded-md font-semibold text-base cursor-pointer hover:bg-yellow-500 transition-colors"
          >
            Submit Solution
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Panel (70%) */}
        <div className="w-[70%] flex-shrink-0 flex flex-col bg-white border-r border-gray-200 h-full overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Problem Section */}
            <div 
              data-tour="problem-description"
              className="flex-shrink-0 p-6 overflow-y-auto border-b border-gray-200 bg-gray-50"
              style={{ maxHeight: '200px' }}
            >
              <div className="mb-3">
                <h2 className="text-xl font-bold text-gray-900 mb-0">{dummyProblem.title}</h2>
              </div>
              <div>
                <p className="text-sm text-gray-700 leading-relaxed m-0">{dummyProblem.description}</p>
              </div>
            </div>

            {/* Canvas and Actions Container */}
            <div className="flex-1 min-h-0 flex flex-col p-6 overflow-hidden">
              {/* Excalidraw Canvas */}
              <div 
                data-tour="canvas"
                className="flex-1 min-h-0 w-full mb-4"
                style={{ pointerEvents: isRunning ? 'none' : 'auto' }}
              >
                <div className="flex flex-col h-full">
                  <div className="px-3 py-2.5 bg-gray-50 border-b border-gray-200 rounded-t-lg">
                    <h3 className="m-0 text-base font-semibold text-gray-800">Architecture Diagram</h3>
                  </div>
                  <div 
                    className="flex-1 overflow-hidden border border-t-0 border-gray-200 rounded-b-lg relative bg-white"
                    style={{ height: '600px', minHeight: '500px' }}
                  >
                    <Excalidraw
                      theme="light"
                      UIOptions={{
                        canvasActions: {
                          loadScene: false,
                          saveToActiveFile: false,
                          export: false,
                          toggleTheme: false,
                        }
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Submit Bar */}
              <div className="flex-shrink-0">
                <div className="flex justify-end">
                  <button 
                    className="px-8 py-3 bg-gray-900 text-white rounded-lg text-base font-semibold cursor-pointer transition-colors hover:bg-gray-800"
                    disabled={isRunning}
                  >
                    Submit Design
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel (30%) - Chat */}
        <div 
          data-tour="chat"
          className="w-[30%] flex-shrink-0 h-full bg-white border-l border-gray-200"
          style={{ pointerEvents: isRunning ? 'none' : 'auto' }}
        >
          <div className="h-full flex flex-col">
            <div className="px-6 py-5 border-b border-gray-200 bg-white">
              <h3 className="text-lg font-semibold text-gray-800 mb-1">Ask Clarifying Questions</h3>
              <p className="text-sm text-gray-600 m-0">Get help understanding the requirements</p>
            </div>
            <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
              <div className="text-center text-gray-500 mt-10">
                <p className="text-sm mb-2">Start by asking clarifying questions about the system design problem.</p>
                <p className="text-xs text-gray-400 italic">The assistant will help you understand the requirements without giving complete solutions.</p>
              </div>
            </div>
            <form className="px-4 py-4 border-t border-gray-200 bg-white flex gap-2.5">
              <input
                type="text"
                placeholder="Ask a question..."
                className="flex-1 px-3 py-3 border border-gray-200 rounded-md text-sm focus:outline-none focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                disabled={isRunning}
              />
              <button
                type="submit"
                className="px-6 py-3 bg-blue-600 text-white rounded-md text-sm font-semibold hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={isRunning}
              >
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

const TourSystemDesignPage = () => {
  return (
    <TourProvider>
      <TourSystemDesignPageContent />
    </TourProvider>
  );
};

export default TourSystemDesignPage;

