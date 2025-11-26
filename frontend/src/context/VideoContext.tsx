import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface VideoContextType {
  videoStream: MediaStream | null;
  setVideoStream: (stream: MediaStream | null) => void;
  requestVideoStream: () => Promise<MediaStream | null>;
}

const VideoContext = createContext<VideoContextType | undefined>(undefined);

interface VideoProviderProps {
  children: ReactNode;
}

export const VideoProvider = ({ children }: VideoProviderProps) => {
  const [videoStream, setVideoStreamState] = useState<MediaStream | null>(null);

  const setVideoStream = useCallback((stream: MediaStream | null) => {
    // Stop previous stream if exists
    if (videoStream) {
      videoStream.getTracks().forEach(track => track.stop());
    }
    setVideoStreamState(stream);
  }, [videoStream]);

  const requestVideoStream = useCallback(async (): Promise<MediaStream | null> => {
    try {
      // If stream already exists and is active, return it
      if (videoStream && videoStream.active) {
        return videoStream;
      }

      // Request new stream
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      });
      setVideoStreamState(stream);
      return stream;
    } catch (err) {
      console.error('Error requesting video stream:', err);
      return null;
    }
  }, [videoStream]);

  const value: VideoContextType = {
    videoStream,
    setVideoStream,
    requestVideoStream,
  };

  return <VideoContext.Provider value={value}>{children}</VideoContext.Provider>;
};

export const useVideo = (): VideoContextType => {
  const context = useContext(VideoContext);
  if (!context) {
    throw new Error('useVideo must be used within VideoProvider');
  }
  return context;
};

