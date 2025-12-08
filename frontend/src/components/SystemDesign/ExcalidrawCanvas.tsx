import { useCallback, useRef, useEffect } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import { useSystemDesign } from '../../context/SystemDesignContext';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ExcalidrawElement = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AppState = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type BinaryFiles = any;

const ExcalidrawCanvas = () => {
  const { updateExcalidrawData } = useSystemDesign();
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced onChange to prevent infinite loops
  const onChange = useCallback((elements: readonly ExcalidrawElement[], appState: AppState, files: BinaryFiles) => {
    // Clear any pending updates
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Debounce the update to avoid excessive state updates
    timeoutRef.current = setTimeout(() => {
      updateExcalidrawData({ elements: [...elements], appState, files });
    }, 300);
  }, [updateExcalidrawData]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Hide the main menu trigger button and library sidebar trigger
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      /* Hide Excalidraw main menu trigger button (library button) */
      button[data-testid="main-menu-trigger"] {
        display: none !important;
      }
      /* Hide Excalidraw library sidebar trigger */
      .sidebar-trigger.default-sidebar-trigger,
      .sidebar-trigger:has(.sidebar-trigger__label:contains("Library")) {
        display: none !important;
      }
    `;
    document.head.appendChild(style);

    // Also use MutationObserver to catch dynamically rendered library sidebar triggers
    const hideLibrarySidebar = () => {
      const sidebarTriggers = document.querySelectorAll('.sidebar-trigger');
      sidebarTriggers.forEach((trigger) => {
        const label = trigger.querySelector('.sidebar-trigger__label');
        if (label && label.textContent?.trim() === 'Library') {
          (trigger as HTMLElement).style.display = 'none';
        }
      });
    };

    // Initial hide
    hideLibrarySidebar();

    // Observe for dynamically added elements
    const observer = new MutationObserver(hideLibrarySidebar);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      document.head.removeChild(style);
      observer.disconnect();
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 bg-gray-50 border-b border-gray-200 rounded-t-lg">
        <h3 className="m-0 text-base font-semibold text-gray-800">Architecture Diagram</h3>
      </div>
      <div 
        className="flex-1 overflow-hidden border border-t-0 border-gray-200 rounded-b-lg relative bg-white"
        style={{ 
          height: '600px',
          minHeight: '500px'
        }}
      >
        <Excalidraw
          onChange={onChange}
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
  );
};

export default ExcalidrawCanvas;