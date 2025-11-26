import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface UseFullscreenWarningOptions {
  onFinalAttempt?: () => void;
}

export const useFullscreenWarning = (options: UseFullscreenWarningOptions = {}) => {
  const { onFinalAttempt } = options;
  const navigate = useNavigate();
  const [showViolation, setShowViolation] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const wasFullscreenRef = useRef(false);
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const navigateRef = useRef(navigate);
  const onFinalAttemptRef = useRef(onFinalAttempt);

  // Keep refs updated
  useEffect(() => {
    navigateRef.current = navigate;
    onFinalAttemptRef.current = onFinalAttempt;
  }, [navigate, onFinalAttempt]);

  useEffect(() => {
    // Track initial fullscreen state
    const checkFullscreen = () => {
      const isFullscreen = !!(
        document.fullscreenElement ||
        (document as any).webkitFullscreenElement ||
        (document as any).mozFullScreenElement ||
        (document as any).msFullscreenElement
      );
      wasFullscreenRef.current = isFullscreen;
    };

    checkFullscreen();

    const handleFullscreenChange = () => {
      const isFullscreen = !!(
        document.fullscreenElement ||
        (document as any).webkitFullscreenElement ||
        (document as any).mozFullScreenElement ||
        (document as any).msFullscreenElement
      );

      // Only trigger if we were in fullscreen and now we're not
      if (wasFullscreenRef.current && !isFullscreen) {
        // Show violation modal with 5 second countdown
        setShowViolation(true);
        setCountdown(5);

        // Clear any existing interval
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current);
          countdownIntervalRef.current = null;
        }

        // Start countdown
        countdownIntervalRef.current = setInterval(() => {
          setCountdown((prev) => {
            const newCount = prev - 1;
            if (newCount <= 0) {
              // Time's up - redirect to completed page
              if (countdownIntervalRef.current) {
                clearInterval(countdownIntervalRef.current);
                countdownIntervalRef.current = null;
              }
              setShowViolation(false);
              if (onFinalAttemptRef.current) {
                onFinalAttemptRef.current();
              }
              navigateRef.current('/test/completed', { replace: true });
              return 0;
            }
            return newCount;
          });
        }, 1000);
      } else if (!wasFullscreenRef.current && isFullscreen) {
        // User returned to fullscreen - close violation modal and reset
        setShowViolation(false);
        setCountdown(5);
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current);
          countdownIntervalRef.current = null;
        }
      }

      wasFullscreenRef.current = isFullscreen;
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
        countdownIntervalRef.current = null;
      }
    };
  }, []); // Empty dependency array - only run once

  const handleRedirect = () => {
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    setShowViolation(false);
    if (onFinalAttemptRef.current) {
      onFinalAttemptRef.current();
    }
    navigateRef.current('/test/completed', { replace: true });
  };

  return {
    showViolation,
    countdown,
    handleRedirect,
  };
};
