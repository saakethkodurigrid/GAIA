interface FullscreenViolationModalProps {
  isOpen: boolean;
  countdown: number;
  onRedirect: () => void;
}

const FullscreenViolationModal = ({ isOpen, countdown }: FullscreenViolationModalProps) => {

  if (!isOpen) return null;

  const requestFullscreen = () => {
    const element = document.documentElement;
    
    // Try standard fullscreen API
    if (element.requestFullscreen) {
      element.requestFullscreen().catch((err: Error) => {
        console.error('Error attempting to enable fullscreen:', err);
      });
      return;
    }
    
    // Try webkit (Chrome/Safari)
    const webkitRequestFullscreen = (element as HTMLElement & { webkitRequestFullscreen?: () => Promise<void> }).webkitRequestFullscreen;
    if (webkitRequestFullscreen) {
      webkitRequestFullscreen.call(element).catch((err: Error) => {
        console.error('Error attempting to enable fullscreen:', err);
      });
      return;
    }
    
    // Try moz (Firefox)
    const mozRequestFullScreen = (element as HTMLElement & { mozRequestFullScreen?: () => Promise<void> }).mozRequestFullScreen;
    if (mozRequestFullScreen) {
      mozRequestFullScreen.call(element).catch((err: Error) => {
        console.error('Error attempting to enable fullscreen:', err);
      });
      return;
    }
    
    // Try ms (IE/Edge)
    const msRequestFullscreen = (element as HTMLElement & { msRequestFullscreen?: () => Promise<void> }).msRequestFullscreen;
    if (msRequestFullscreen) {
      msRequestFullscreen.call(element).catch((err: Error) => {
        console.error('Error attempting to enable fullscreen:', err);
      });
    }
  };

  const handleReturnToFullscreen = () => {
    requestFullscreen();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
        <div className="flex items-center justify-center mb-6">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center">
            <svg 
              className="w-10 h-10 text-red-600" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
              />
            </svg>
          </div>
        </div>

        <h2 className="text-3xl font-bold text-red-600 text-center mb-4">
          Fullscreen Required
        </h2>

        <p className="text-gray-700 text-center mb-6 text-lg">
          You must return to fullscreen mode immediately. The interview will end if you don't return within:
        </p>

        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-6 mb-6">
          <p className="text-center text-red-800 font-semibold text-base mb-2">
            Time remaining:
          </p>
          <div className="flex items-center justify-center">
            <div className="text-5xl font-bold text-red-600">
              {countdown}
            </div>
            <span className="text-2xl font-semibold text-red-600 ml-2">
              {countdown === 1 ? 'second' : 'seconds'}
            </span>
          </div>
        </div>

        <button
          onClick={handleReturnToFullscreen}
          className="w-full bg-yellow-500 text-white py-3 px-6 rounded-lg font-semibold text-base hover:bg-yellow-600 transition-colors shadow-md mb-4"
        >
          Return to Fullscreen
        </button>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            If you don't return to fullscreen, the interview will be automatically ended.
          </p>
        </div>
      </div>
    </div>
  );
};

export default FullscreenViolationModal;
