import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface UseFullscreenWarningOptions {
  onFinalAttempt?: () => void;
}

const WARNING_STORAGE_KEY = 'fullscreenWarning';
const WARNING_DURATION = 5000; // 5 seconds in milliseconds

interface WarningState {
  active: boolean;
  startTime: number;
}

const clearWarningStorage = () => {
  try {
    localStorage.removeItem(WARNING_STORAGE_KEY);
  } catch (error) {
    console.error('Error clearing warning storage:', error);
  }
};

const saveWarningState = (startTime: number) => {
  try {
    const state: WarningState = {
      active: true,
      startTime,
    };
    localStorage.setItem(WARNING_STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Error saving warning state:', error);
  }
};

const getWarningState = (): WarningState | null => {
  try {
    const stored = localStorage.getItem(WARNING_STORAGE_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as WarningState;
  } catch (error) {
    console.error('Error reading warning state:', error);
    return null;
  }
};

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

  // Check for persisted warning state on mount
  useEffect(() => {
    const warningState = getWarningState();
    if (warningState && warningState.active) {
      const now = Date.now();
      const elapsed = now - warningState.startTime;
      const remaining = WARNING_DURATION - elapsed;

      if (remaining <= 0) {
        // Time has already passed - end test immediately
        clearWarningStorage();
        if (onFinalAttemptRef.current) {
          onFinalAttemptRef.current();
        }
        navigateRef.current('/test/completed', { replace: true });
        return;
      }

      // Restore warning state and resume countdown
      const remainingSeconds = Math.ceil(remaining / 1000);
      setShowViolation(true);
      setCountdown(remainingSeconds);

      // Start countdown from remaining time
      countdownIntervalRef.current = setInterval(() => {
        setCountdown((prev) => {
          const newCount = prev - 1;
          if (newCount <= 0) {
            // Time's up - redirect to completed page
            if (countdownIntervalRef.current) {
              clearInterval(countdownIntervalRef.current);
              countdownIntervalRef.current = null;
            }
            clearWarningStorage();
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
    }
  }, []);

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
        const startTime = Date.now();
        setShowViolation(true);
        setCountdown(5);
        
        // Save warning state to localStorage
        saveWarningState(startTime);

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
              clearWarningStorage();
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
        clearWarningStorage();
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
    clearWarningStorage();
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
