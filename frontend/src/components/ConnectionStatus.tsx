import { useState, useEffect } from 'react';

/**
 * ConnectionStatus Component
 * 
 * Displays a banner at the top of the screen when internet connection is lost or restored.
 * - Shows red warning when offline
 * - Shows green confirmation when connection is restored
 * - Auto-hides after 5 seconds when online
 * - Persists while offline
 */
export const ConnectionStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [showBanner, setShowBanner] = useState(!navigator.onLine);
  const [justReconnected, setJustReconnected] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      console.log('🟢 Connection restored');
      setIsOnline(true);
      setShowBanner(true);
      setJustReconnected(true);

      // Hide the "connected" banner after 5 seconds
      setTimeout(() => {
        setShowBanner(false);
        setJustReconnected(false);
      }, 5000);
    };

    const handleOffline = () => {
      console.log('🔴 Connection lost');
      setIsOnline(false);
      setShowBanner(true);
      setJustReconnected(false);
    };

    // Listen for online/offline events
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Cleanup listeners
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Don't show banner if online and not just reconnected
  if (!showBanner) return null;

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 px-4 py-3 text-center text-white text-sm font-medium shadow-lg transition-all duration-300 ${
        isOnline && justReconnected
          ? 'bg-green-600'
          : 'bg-red-600 animate-pulse'
      }`}
      role="alert"
      aria-live="assertive"
    >
      {isOnline && justReconnected ? (
        <div className="flex items-center justify-center gap-2">
          <svg
            className="w-5 h-5"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <span>
            ✅ Connection restored! Your answers are being saved to the server.
          </span>
        </div>
      ) : (
        <div className="flex items-center justify-center gap-2">
          <svg
            className="w-5 h-5"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <span>
            ⚠️ No internet connection! Your answers are saved locally but cannot be uploaded to the server. Please reconnect soon.
          </span>
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;

