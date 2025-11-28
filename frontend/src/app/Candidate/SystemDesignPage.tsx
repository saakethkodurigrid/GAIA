import { useNavigate } from 'react-router-dom';
import { SystemDesignProvider, useSystemDesign } from '../../context/SystemDesignContext';
import { useVideo } from '../../context/VideoContext';
import DesignHeader from '../../components/SystemDesign/DesignHeader';
import ExcalidrawCanvas from '../../components/SystemDesign/ExcalidrawCanvas';
import ClarifyingChat from '../../components/SystemDesign/ClarifyingChat';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';
import { useFullscreenWarning } from '../../hooks/useFullscreenWarning';
import FullscreenViolationModal from '../../components/FullscreenViolationModal';

const SystemDesignPageContent = () => {
  const { problem, isLoading, submitSolution } = useSystemDesign();
  const { videoStream, requestVideoStream } = useVideo();
  const navigate = useNavigate();

  const handleSubmit = async () => {
    try {
      await submitSolution();
      // Navigate back to test overview page after successful submission
      navigate('/test-overview');
    } catch (error) {
      console.error('Failed to submit solution:', error);
      // You could show an error message to the user here
    }
  };

  // Monitor fullscreen exit with 5 second countdown
  const { showViolation, countdown, handleRedirect } = useFullscreenWarning({
    onFinalAttempt: () => {
      // This will be called when time runs out
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-gray-600">Loading problem...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen max-w-full flex flex-col bg-gray-50 overflow-hidden m-0 p-0">
      {/* Header */}
      <DesignHeader onSubmit={handleSubmit} />

      {/* Main Content */}
      <div className="flex flex-1 w-full max-w-full h-0 m-0 p-0 overflow-hidden relative">
        {/* Left Panel (70%) */}
        <div className="w-[70%] flex-shrink-0 flex flex-col bg-white border-r border-gray-200 h-full overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Problem Section - Fixed height, scrollable */}
            <div className="flex-shrink-0 p-6 overflow-y-auto border-b border-gray-200 bg-gray-50" style={{ maxHeight: '200px' }}>
              <div className="mb-3">
                <h2 className="text-xl font-bold text-gray-900 mb-0">{problem?.title}</h2>
              </div>
              <div>
                <p className="text-sm text-gray-700 leading-relaxed m-0">{problem?.description}</p>
              </div>
            </div>

            {/* Canvas Container */}
            <div className="flex-1 min-h-0 flex flex-col p-6 overflow-hidden">
              {/* Excalidraw Canvas - Takes all space */}
              <div className="flex-1 min-h-0 w-full">
                <ExcalidrawCanvas />
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel (30%) - Chat */}
        <div className="w-[30%] flex-shrink-0 h-full bg-white border-l border-gray-200">
          <ClarifyingChat />
        </div>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0">
        <Footer />
      </div>

      {/* Fullscreen Violation Modal */}
      <FullscreenViolationModal
        isOpen={showViolation}
        countdown={countdown}
        onRedirect={handleRedirect}
      />

      {/* Video Preview Component */}
      <VideoPreview 
        videoStream={videoStream} 
        onStreamRequest={requestVideoStream}
      />
    </div>
  );
};

const SystemDesignPage = () => {
  return (
    <SystemDesignProvider>
      <SystemDesignPageContent />
    </SystemDesignProvider>
  );
};

export default SystemDesignPage;

