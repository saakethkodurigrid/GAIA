import { useState, useEffect } from 'react';

export interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message?: string;
  customContent?: React.ReactNode;
  confirmButtonText?: string;
  confirmButtonColor?: 'yellow' | 'green' | 'orange';
  cancelButtonText?: string;
  isSubmitting?: boolean;
  disabled?: boolean;
}

const ConfirmationModal = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  customContent,
  confirmButtonText = 'Submit',
  confirmButtonColor = 'yellow',
  cancelButtonText = 'Cancel',
  isSubmitting = false,
  disabled = false,
}: ConfirmationModalProps) => {
  const [confirmText, setConfirmText] = useState('');

  // Reset confirmation text when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setConfirmText('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (confirmText !== 'Submit') {
      return;
    }
    onConfirm();
  };

  const handleClose = () => {
    setConfirmText('');
    onClose();
  };

  const getConfirmButtonClasses = () => {
    const baseClasses = 'px-6 py-3 rounded-lg text-base font-medium cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
    
    switch (confirmButtonColor) {
      case 'green':
        return `${baseClasses} bg-green-600 text-white hover:bg-green-700`;
      case 'orange':
        return `${baseClasses} bg-orange-500 text-white hover:bg-orange-600`;
      case 'yellow':
      default:
        return `${baseClasses} bg-yellow-400 text-gray-900 hover:bg-yellow-500`;
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1000]" 
      onClick={handleClose}
    >
      <div 
        className="bg-white rounded-xl p-8 max-w-[500px] w-[90%] shadow-[0_10px_25px_rgba(0,0,0,0.2)]" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with warning icon */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-800">{title}</h2>
        </div>

        {/* Content */}
        <div className="mb-6">
          {customContent || (message && <p className="text-gray-700 mb-4">{message}</p>)}
          
          <p className="text-gray-700 mb-4 font-medium">
            Please type "Submit" (case-sensitive) to confirm:
          </p>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Type 'Submit' to confirm"
            className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg text-base focus:outline-none focus:border-yellow-500 focus:ring-2 focus:ring-yellow-200"
            autoFocus
            disabled={isSubmitting || disabled}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && confirmText === 'Submit' && !isSubmitting && !disabled) {
                handleConfirm();
              }
            }}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-4">
          <button 
            className="px-6 py-3 bg-gray-100 border border-gray-200 rounded-lg text-base font-medium cursor-pointer transition-all hover:bg-gray-200 text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed" 
            onClick={handleClose} 
            disabled={isSubmitting}
          >
            {cancelButtonText}
          </button>
          <button
            className={getConfirmButtonClasses()}
            onClick={handleConfirm}
            disabled={isSubmitting || disabled || confirmText !== 'Submit'}
          >
            {isSubmitting ? 'Submitting...' : confirmButtonText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;

