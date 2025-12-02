/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, type ReactNode } from 'react';
import { useCheatingDetection, type CheatingEvent } from '../hooks/useCheatingDetection';
import { useVideo } from './VideoContext';

interface CheatingDetectionContextType {
  status: {
    multipleFacesDetected: boolean;
    isTabSwitched: boolean;
    isWindowBlurred: boolean;
    faceCount: number;
    isInitialized: boolean;
    error: string | null;
  };
  events: CheatingEvent[];
  clearEvents: () => void;
  getEvents: () => CheatingEvent[];
}

const CheatingDetectionContext = createContext<CheatingDetectionContextType | undefined>(
  undefined
);

interface CheatingDetectionProviderProps {
  children: ReactNode;
  enabled?: boolean;
}

export const CheatingDetectionProvider = ({
  children,
  enabled = true,
}: CheatingDetectionProviderProps) => {
  const { videoStream } = useVideo();
  const cheatingDetection = useCheatingDetection(videoStream, enabled);

  return (
    <CheatingDetectionContext.Provider value={cheatingDetection}>
      {children}
    </CheatingDetectionContext.Provider>
  );
};

export const useCheatingDetectionContext = (): CheatingDetectionContextType => {
  const context = useContext(CheatingDetectionContext);
  if (!context) {
    throw new Error('useCheatingDetectionContext must be used within CheatingDetectionProvider');
  }
  return context;
};

