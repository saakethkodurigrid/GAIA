import { useEffect } from 'react';

interface RecoveryToastProps {
  show: boolean;
  message: string;
  onClose: () => void;
  duration?: number; // Auto-hide duration in milliseconds
}

/**
 * RecoveryToast Component
 * 
 * Shows a temporary notification when connection recovery completes.
 * Auto-hides after specified duration.
 */
export const RecoveryToast = ({ show, message, onClose, duration = 4000 }: RecoveryToastProps) => {
  useEffect(() => {
    if (show && duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [show, duration, onClose]);

  if (!show) return null;

  return (
    <div
      className="fixed bottom-6 right-6 z-50 animate-slide-up"
      role="alert"
      aria-live="polite"
    >
      <div className="bg-green-600 text-white px-6 py-4 rounded-lg shadow-2xl flex items-center gap-3 max-w-md">
        {/* Success Icon */}
        <svg
          className="w-6 h-6 flex-shrink-0"
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

        {/* Message */}
        <div className="flex-1">
          <p className="font-medium text-sm">{message}</p>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="flex-shrink-0 text-white hover:text-green-100 transition-colors"
          aria-label="Close notification"
        >
          <svg
            className="w-5 h-5"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default RecoveryToast;

