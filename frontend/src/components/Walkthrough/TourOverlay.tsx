import { useEffect, useRef, useState } from 'react';
import { useTour } from '../../context/TourContext';
import StepTooltip from './StepTooltip';

const TourOverlay = () => {
  const { isRunning, currentStep, steps, stopTour } = useTour();
  const overlayRef = useRef<HTMLDivElement>(null);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    let updateTimeout: ReturnType<typeof setTimeout>;
    let updateRect: (() => void) | null = null;

    if (isRunning && steps.length > 0) {
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
      
      // Scroll to target element and update position smoothly
      const currentStepData = steps[currentStep];
      if (currentStepData) {
        updateRect = () => {
          const targetElement = document.querySelector(currentStepData.target);
          if (targetElement) {
            // First, scroll into view smoothly
            targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Wait for scroll and layout to complete before calculating position
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                const rect = targetElement.getBoundingClientRect();
                // Only update if we have valid dimensions
                if (rect.width > 0 && rect.height > 0) {
                  setTargetRect(rect);
                }
              });
            });
          }
        };
        
        // Update position with a small delay to ensure DOM is ready
        updateTimeout = setTimeout(updateRect, 50);
        
        window.addEventListener('resize', updateRect);
        window.addEventListener('scroll', updateRect, true);
      }
      
      return () => {
        if (updateTimeout) clearTimeout(updateTimeout);
        if (updateRect) {
          window.removeEventListener('resize', updateRect);
          window.removeEventListener('scroll', updateRect, true);
        }
        document.body.style.overflow = '';
      };
    } else {
      document.body.style.overflow = '';
      setTargetRect(null);
    }
  }, [isRunning, currentStep, steps]);

  if (!isRunning || steps.length === 0) {
    return null;
  }

  const currentStepData = steps[currentStep];
  // Show overlay even while positioning - keep it visible for smooth transitions
  if (!currentStepData || !targetRect) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-[9998] transition-opacity duration-300" />
    );
  }

  return (
    <>
      {/* Dark overlay with spotlight */}
      <div
        ref={overlayRef}
        className="fixed inset-0 bg-black bg-opacity-60 z-[9998] transition-all duration-500 ease-in-out"
        style={{
          clipPath: `polygon(
            0% 0%, 
            0% 100%, 
            ${targetRect.left}px 100%, 
            ${targetRect.left}px ${targetRect.top}px, 
            ${targetRect.right}px ${targetRect.top}px, 
            ${targetRect.right}px ${targetRect.bottom}px, 
            ${targetRect.left}px ${targetRect.bottom}px, 
            ${targetRect.left}px 100%, 
            100% 100%, 
            100% 0%
          )`
        }}
        onClick={(e) => {
          // Prevent closing on overlay click
          e.stopPropagation();
        }}
      />

      {/* Highlight border around target */}
      <div
        className="fixed z-[9997] border-4 border-blue-500 rounded-lg pointer-events-none transition-all duration-500 ease-in-out"
        style={{
          left: `${targetRect.left - 4}px`,
          top: `${targetRect.top - 4}px`,
          width: `${targetRect.width + 8}px`,
          height: `${targetRect.height + 8}px`,
          boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.5)'
        }}
      />

      {/* Tooltip - always render when we have targetRect for smooth transitions */}
      <StepTooltip
        step={currentStepData}
        stepIndex={currentStep}
        totalSteps={steps.length}
        targetRect={targetRect}
        onNext={() => {
          if (currentStep < steps.length - 1) {
            // Will be handled by parent
          } else {
            stopTour();
          }
        }}
        onPrevious={() => {
          // Will be handled by parent
        }}
        onClose={stopTour}
      />
    </>
  );
};

export default TourOverlay;


