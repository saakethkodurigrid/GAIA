import { useNavigate, useLocation } from 'react-router-dom';
import { useTour } from '../../context/TourContext';
import type { TourStep } from '../../context/TourContext';

interface StepTooltipProps {
  step: TourStep;
  stepIndex: number;
  totalSteps: number;
  targetRect: DOMRect;
  onNext: () => void;
  onPrevious: () => void;
  onClose: () => void;
}

const StepTooltip = ({ step, stepIndex, totalSteps, targetRect, onNext, onPrevious, onClose }: StepTooltipProps) => {
  const { nextStep, previousStep } = useTour();
  const navigate = useNavigate();
  const location = useLocation();
  const isLastStep = stepIndex === totalSteps - 1;

  // For the last step, always center it
  const placement = isLastStep ? 'center' : (step.placement || 'bottom');
  
  // Tooltip dimensions (approximate)
  const tooltipWidth = 384; // max-w-sm = 384px
  const tooltipHeight = 200; // approximate height
  const padding = 20;
  
  let tooltipStyle: React.CSSProperties = {};
  
  switch (placement) {
    case 'top': {
      const left = targetRect.left + targetRect.width / 2;
      const bottom = window.innerHeight - targetRect.top + padding;
      // Ensure tooltip doesn't go off left/right edges
      const adjustedLeft = Math.max(padding, Math.min(left, window.innerWidth - tooltipWidth / 2 - padding));
      tooltipStyle = {
        bottom: Math.min(bottom, window.innerHeight - padding),
        left: adjustedLeft,
        transform: 'translateX(-50%)',
        maxWidth: '90vw'
      };
      break;
    }
    case 'bottom': {
      const left = targetRect.left + targetRect.width / 2;
      const spaceBelow = window.innerHeight - targetRect.bottom - padding;
      const spaceAbove = targetRect.top - padding;
      
      // If not enough space below but enough above, position above instead
      if (spaceBelow < tooltipHeight && spaceAbove > tooltipHeight) {
        const adjustedLeft = Math.max(tooltipWidth / 2 + padding, Math.min(left, window.innerWidth - tooltipWidth / 2 - padding));
        tooltipStyle = {
          bottom: window.innerHeight - targetRect.top + padding,
          left: adjustedLeft,
          transform: 'translateX(-50%)',
          maxWidth: '90vw'
        };
      } else {
        // Position below (or as close as possible)
        const top = targetRect.bottom + padding;
        const adjustedLeft = Math.max(tooltipWidth / 2 + padding, Math.min(left, window.innerWidth - tooltipWidth / 2 - padding));
        tooltipStyle = {
          top: Math.min(top, window.innerHeight - tooltipHeight - padding),
          left: adjustedLeft,
          transform: 'translateX(-50%)',
          maxWidth: '90vw'
        };
      }
      break;
    }
    case 'left': {
      const top = targetRect.top + targetRect.height / 2;
      const right = window.innerWidth - targetRect.left + padding;
      tooltipStyle = {
        top: Math.max(padding, Math.min(top, window.innerHeight - tooltipHeight / 2 - padding)),
        right: Math.min(right, window.innerWidth - padding),
        transform: 'translateY(-50%)',
        maxWidth: '90vw'
      };
      break;
    }
    case 'right': {
      const top = targetRect.top + targetRect.height / 2;
      const left = targetRect.right + padding;
      tooltipStyle = {
        top: Math.max(padding, Math.min(top, window.innerHeight - tooltipHeight / 2 - padding)),
        left: Math.min(left, window.innerWidth - tooltipWidth - padding),
        transform: 'translateY(-50%)',
        maxWidth: '90vw'
      };
      break;
    }
    case 'center':
      tooltipStyle = {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        maxWidth: '90vw'
      };
      break;
    case 'left-side':
      // Position on the left side of the screen, below the target element (options)
      const leftSidePadding = 40; // More padding to overlap sidebar nicely
      const topPosition = targetRect.bottom + padding; // Position below the options
      tooltipStyle = {
        top: Math.min(topPosition, window.innerHeight - tooltipHeight - padding),
        left: leftSidePadding,
        maxWidth: '400px',
        width: 'auto'
      };
      break;
  }

  const handleNext = () => {
    if (isLastStep) {
      onClose();
      // Navigate based on which tour is completed
      setTimeout(() => {
        if (location.pathname === '/tutorial/system-design') {
          // System design tour is the last one, navigate to test ready page
          navigate('/test/ready');
        } else if (location.pathname === '/tutorial/mcq') {
          // MCQ tour completed, navigate to coding tour
          navigate('/tutorial/coding');
        } else if (location.pathname === '/tutorial/coding') {
          // Coding tour completed, navigate to system design tour
          navigate('/tutorial/system-design');
        } else {
          // Default fallback
          navigate('/');
        }
      }, 300);
    } else {
      nextStep();
      onNext();
    }
  };

  const handlePrevious = () => {
    previousStep();
    onPrevious();
  };

  return (
    <div
      className="fixed z-[10000] bg-white rounded-lg shadow-2xl p-6 max-w-sm"
      style={{
        ...tooltipStyle,
        position: 'fixed'
      }}
    >
      {step.title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{step.title}</h3>
      )}
      <p className="text-sm text-gray-700 mb-4">{step.content}</p>
      
      <div className={`flex items-center ${isLastStep ? 'justify-center' : 'justify-between'}`}>
        {!isLastStep && (
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevious}
              disabled={stepIndex === 0}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <button
              onClick={handleNext}
              className="px-4 py-2 text-sm font-medium text-gray-900 bg-yellow-400 rounded-md hover:bg-yellow-500 transition-colors"
            >
              Next
            </button>
          </div>
        )}
        {isLastStep && (
          <button
            onClick={handleNext}
            className="px-6 py-2 text-sm font-medium text-gray-900 bg-yellow-400 rounded-md hover:bg-yellow-500 transition-colors"
          >
            Done
          </button>
        )}
        {!isLastStep && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      
      <div className="mt-4 flex justify-center gap-1">
        {Array.from({ length: totalSteps }).map((_, index) => (
          <div
            key={index}
            className={`h-2 w-2 rounded-full transition-all ${
              index === stepIndex ? 'bg-yellow-400' : 'bg-gray-300'
            }`}
          />
        ))}
      </div>
    </div>
  );
};

export default StepTooltip;

