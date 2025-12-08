import { useState, useEffect, useRef } from 'react';
import { useFaceDetection } from '../../hooks/useFaceDetection';

interface VideoPreviewProps {
  videoStream: MediaStream | null;
  onStreamRequest?: () => Promise<MediaStream | null>;
}

const VideoPreview = ({ videoStream, onStreamRequest }: VideoPreviewProps) => {
  // Auto-show video when stream is available for face detection
  const [isVisible, setIsVisible] = useState(false);
  const [localStream, setLocalStream] = useState<MediaStream | null>(videoStream);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hiddenVideoRef = useRef<HTMLVideoElement>(null); // Hidden video for face detection
  const [videoElement, setVideoElement] = useState<HTMLVideoElement | null>(null);

  // Update videoElement state when video is ready and playing
  useEffect(() => {
    console.log('[VideoPreview] Video element effect', { isVisible, hasStream: !!localStream, hasVideoRef: !!videoRef.current });
    
    const video = videoRef.current;
    if (video && isVisible && localStream) {
      const handleLoadedMetadata = () => {
        console.log('[VideoPreview] Video metadata loaded', {
          videoWidth: video.videoWidth,
          videoHeight: video.videoHeight,
          readyState: video.readyState,
        });
        setVideoElement(video);
      };

      const handlePlay = () => {
        console.log('[VideoPreview] Video started playing');
        setVideoElement(video);
      };

      const handleCanPlay = () => {
        console.log('[VideoPreview] Video can play');
        setVideoElement(video);
      };

      video.addEventListener('loadedmetadata', handleLoadedMetadata);
      video.addEventListener('play', handlePlay);
      video.addEventListener('canplay', handleCanPlay);

      // Also set immediately if already loaded
      if (video.readyState >= 2) {
        console.log('[VideoPreview] Video already ready, setting element immediately');
        setVideoElement(video);
      }

      return () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata);
        video.removeEventListener('play', handlePlay);
        video.removeEventListener('canplay', handleCanPlay);
      };
    } else {
      console.log('[VideoPreview] Clearing video element', { hasVideo: !!video, isVisible, hasStream: !!localStream });
      setVideoElement(null);
    }
  }, [isVisible, localStream]);

  // Note: We don't auto-show the video anymore since face detection works via hidden video
  // User can manually show/hide the video preview, and face detection will continue working

  // Track hidden video element for face detection
  const [hiddenVideoElement, setHiddenVideoElement] = useState<HTMLVideoElement | null>(null);

  // Create hidden video element for face detection (works even when preview is hidden)
  useEffect(() => {
    const hiddenVideo = hiddenVideoRef.current;
    if (localStream && hiddenVideo) {
      hiddenVideo.srcObject = localStream;
      hiddenVideo.play().catch(err => {
        console.error('Error playing hidden video for face detection:', err);
      });

      const handleLoadedMetadata = () => {
        console.log('[VideoPreview] Hidden video metadata loaded for face detection');
        setHiddenVideoElement(hiddenVideo);
      };

      const handlePlay = () => {
        console.log('[VideoPreview] Hidden video started playing for face detection');
        setHiddenVideoElement(hiddenVideo);
      };

      hiddenVideo.addEventListener('loadedmetadata', handleLoadedMetadata);
      hiddenVideo.addEventListener('play', handlePlay);

      // Set immediately if already loaded
      if (hiddenVideo.readyState >= 2) {
        setHiddenVideoElement(hiddenVideo);
      }

      return () => {
        hiddenVideo.removeEventListener('loadedmetadata', handleLoadedMetadata);
        hiddenVideo.removeEventListener('play', handlePlay);
      };
    } else {
      setHiddenVideoElement(null);
    }
  }, [localStream]);

  // Use visible video element if available, otherwise use hidden video for face detection
  const faceDetectionVideoElement = videoElement || hiddenVideoElement;
  
  // Enable face detection when stream is available (works with both visible and hidden video)
  useFaceDetection(faceDetectionVideoElement, !!localStream);

  useEffect(() => {
    // Use provided stream or request new one
    if (videoStream) {
      setLocalStream(videoStream);
    } else if (onStreamRequest && isVisible && !localStream) {
      // Request stream when made visible and no stream available
      onStreamRequest().then(stream => {
        if (stream) {
          setLocalStream(stream);
        }
      });
    }
  }, [videoStream, isVisible, onStreamRequest, localStream]);

  // Set video stream when available
  useEffect(() => {
    if (isVisible && localStream && videoRef.current) {
      videoRef.current.srcObject = localStream;
      videoRef.current.play().catch(err => {
        console.error('Error playing video:', err);
      });
    } else if (videoRef.current && !isVisible) {
      // Clear video when hidden
      videoRef.current.srcObject = null;
    }
  }, [isVisible, localStream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (localStream && !videoStream) {
        // Only stop stream if we created it locally
        localStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [localStream, videoStream]);

  const toggleVisibility = () => {
    setIsVisible(!isVisible);
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Toggle Button */}
      <button
        onClick={toggleVisibility}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg hover:bg-blue-700 transition-colors flex items-center gap-2 mb-2"
        title={isVisible ? 'Hide Video' : 'Show Video'}
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          {isVisible ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.736m0 0L21 21"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          )}
        </svg>
        <span className="text-sm font-medium">
          {isVisible ? 'Hide Video' : 'Show Video'}
        </span>
      </button>

      {/* Hidden video element for face detection (always active when stream is available) */}
      {localStream && (
        <video
          ref={hiddenVideoRef}
          autoPlay
          playsInline
          muted
          className="hidden"
          style={{ position: 'absolute', width: '1px', height: '1px', opacity: 0, pointerEvents: 'none' }}
        />
      )}

      {/* Video Preview */}
      {isVisible && (
        <div className="bg-white rounded-lg shadow-2xl border-2 border-gray-300 overflow-hidden">
          <div className="bg-gray-800 w-64 h-48 relative">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
            {!localStream && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
                <div className="text-white text-sm">Loading camera...</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoPreview;

