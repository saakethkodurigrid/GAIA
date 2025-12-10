import { useState, useEffect, useRef, useCallback } from 'react';
import * as tf from '@tensorflow/tfjs';
import * as faceDetection from '@tensorflow-models/face-detection';

export type CheatingEventType = 'multiple_faces' | 'tab_switch' | 'window_blur' | 'window_focus';

export interface CheatingEvent {
  type: CheatingEventType;
  timestamp: number;
  details: {
    faceCount?: number;
    duration?: number; // For tab switch/blur events
    [key: string]: any;
  };
}

interface CheatingDetectionStatus {
  multipleFacesDetected: boolean;
  isTabSwitched: boolean;
  isWindowBlurred: boolean;
  faceCount: number;
  isInitialized: boolean;
  error: string | null;
}

const STORAGE_KEY = 'cheating_detection_events';
const MAX_STORAGE_EVENTS = 1000; // Limit stored events to prevent localStorage overflow

export const useCheatingDetection = (videoStream: MediaStream | null, enabled: boolean = true) => {
  const [status, setStatus] = useState<CheatingDetectionStatus>({
    multipleFacesDetected: false,
    isTabSwitched: false,
    isWindowBlurred: false,
    faceCount: 0,
    isInitialized: false,
    error: null,
  });

  const [events, setEvents] = useState<CheatingEvent[]>([]);
  const detectorRef = useRef<faceDetection.FaceDetector | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const tabSwitchStartTimeRef = useRef<number | null>(null);
  const isWindowBlurredRef = useRef<boolean>(false);
  const isTabSwitchedRef = useRef<boolean>(false);

  // Load events from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsedEvents = JSON.parse(stored) as CheatingEvent[];
        setEvents(parsedEvents);
      }
    } catch (error) {
      console.error('Error loading cheating detection events from localStorage:', error);
    }
  }, []);

  // Persist events to localStorage whenever events change
  useEffect(() => {
    try {
      // Keep only the most recent events to prevent localStorage overflow
      const eventsToStore = events.slice(-MAX_STORAGE_EVENTS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(eventsToStore));
    } catch (error) {
      console.error('Error saving cheating detection events to localStorage:', error);
    }
  }, [events]);

  // Log event helper
  const logEvent = useCallback((type: CheatingEventType, details: CheatingEvent['details']) => {
    const event: CheatingEvent = {
      type,
      timestamp: Date.now(),
      details,
    };
    setEvents((prev) => [...prev, event]);
  }, []);

  // Initialize TensorFlow.js and face detection model
  useEffect(() => {
    if (!enabled || !videoStream) return;

    let isMounted = true;

    const initializeDetector = async () => {
      try {
        // Initialize TensorFlow.js backend
        await tf.ready();

        // Create face detector with lightweight model
        // Using MediaPipeFaceDetector with TensorFlow.js runtime (more reliable than mediapipe runtime)
        const detector = await faceDetection.createDetector(
          faceDetection.SupportedModels.MediaPipeFaceDetector,
          {
            runtime: 'tfjs',
            modelType: 'short',
          }
        );

        if (!isMounted) {
          detector.dispose();
          return;
        }

        detectorRef.current = detector;

        // Create video element to process the stream
        const video = document.createElement('video');
        video.srcObject = videoStream;
        video.autoplay = true;
        video.playsInline = true;
        video.muted = true;
        videoRef.current = video;

        // Create canvas for face detection
        const canvas = document.createElement('canvas');
        canvasRef.current = canvas;

        video.addEventListener('loadedmetadata', async () => {
          if (isMounted && canvas) {
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            try {
              // Ensure video is playing for face detection
              await video.play();
              setStatus((prev) => ({ ...prev, isInitialized: true, error: null }));
            } catch (playError) {
              console.error('Error playing video:', playError);
              if (isMounted) {
                setStatus((prev) => ({
                  ...prev,
                  error: 'Failed to play video stream',
                }));
              }
            }
          }
        });

        video.addEventListener('error', (e) => {
          console.error('Video element error:', e);
          if (isMounted) {
            setStatus((prev) => ({
              ...prev,
              error: 'Failed to load video stream',
            }));
          }
        });
      } catch (error) {
        console.error('Error initializing face detection:', error);
        if (isMounted) {
          setStatus((prev) => ({
            ...prev,
            error: error instanceof Error ? error.message : 'Failed to initialize face detection',
          }));
        }
      }
    };

    initializeDetector();

    return () => {
      isMounted = false;
      if (detectorRef.current) {
        detectorRef.current.dispose();
        detectorRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
        videoRef.current = null;
      }
      if (canvasRef.current) {
        canvasRef.current = null;
      }
    };
  }, [enabled, videoStream]);

  // Face detection loop
  useEffect(() => {
    if (!enabled || !detectorRef.current || !videoRef.current || !canvasRef.current) return;

    let lastMultipleFacesState = false;

    const detectFaces = async () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const detector = detectorRef.current;

      if (!video || !canvas || !detector) {
        animationFrameRef.current = requestAnimationFrame(detectFaces);
        return;
      }

      // Check if video is ready
      if (video.readyState < video.HAVE_CURRENT_DATA) {
        animationFrameRef.current = requestAnimationFrame(detectFaces);
        return;
      }

      try {
        // Ensure canvas dimensions match video
        if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
          canvas.width = video.videoWidth || 640;
          canvas.height = video.videoHeight || 480;
        }

        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        }

        // Detect faces
        const faces = await detector.estimateFaces(canvas, {
          flipHorizontal: false,
        });

        const faceCount = faces.length;
        const hasMultipleFaces = faceCount > 1;

        // Console log face detection results
        console.log(`[Face Detection] Faces detected: ${faceCount}`, {
          faceCount,
          hasMultipleFaces,
          faces: faces.map((face, idx) => ({
            index: idx,
            boundingBox: face.box,
          })),
        });

        // Update status
        setStatus((prev) => ({
          ...prev,
          faceCount,
          multipleFacesDetected: hasMultipleFaces,
        }));

        // Log event if multiple faces detected (only on state change)
        if (hasMultipleFaces && !lastMultipleFacesState) {
          logEvent('multiple_faces', { faceCount });
          lastMultipleFacesState = true;
        } else if (!hasMultipleFaces && lastMultipleFacesState) {
          lastMultipleFacesState = false;
        }
      } catch (error) {
        console.error('Error detecting faces:', error);
      }

      animationFrameRef.current = requestAnimationFrame(detectFaces);
    };

    detectFaces();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [enabled, logEvent]);

  // Tab switch and window blur detection
  useEffect(() => {
    if (!enabled) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Tab switched or window blurred
        tabSwitchStartTimeRef.current = Date.now();
        isTabSwitchedRef.current = true;
        isWindowBlurredRef.current = true;

        setStatus((prev) => ({
          ...prev,
          isTabSwitched: true,
          isWindowBlurred: true,
        }));

        logEvent('tab_switch', {});
      } else {
        // Tab/window focused again
        const duration = tabSwitchStartTimeRef.current
          ? Date.now() - tabSwitchStartTimeRef.current
          : 0;

        if (isTabSwitchedRef.current) {
          logEvent('window_focus', { duration });
        }

        tabSwitchStartTimeRef.current = null;
        isTabSwitchedRef.current = false;
        isWindowBlurredRef.current = false;

        setStatus((prev) => ({
          ...prev,
          isTabSwitched: false,
          isWindowBlurred: false,
        }));
      }
    };

    const handleBlur = () => {
      if (!document.hidden) {
        // Window blurred but tab still visible (e.g., user clicked another window)
        isWindowBlurredRef.current = true;
        setStatus((prev) => ({
          ...prev,
          isWindowBlurred: true,
        }));
        logEvent('window_blur', {});
      }
    };

    const handleFocus = () => {
      if (isWindowBlurredRef.current && !document.hidden) {
        isWindowBlurredRef.current = false;
        setStatus((prev) => ({
          ...prev,
          isWindowBlurred: false,
        }));
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
    };
  }, [enabled, logEvent]);

  // Clear events function
  const clearEvents = useCallback(() => {
    setEvents([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  // Get events function
  const getEvents = useCallback(() => {
    return events;
  }, [events]);

  // Get cheating event counts function
  const getCheatingEventCounts = useCallback(() => {
    const multipleFacesCount = events.filter(
      (event) => event.type === 'multiple_faces'
    ).length;
    const tabChangeCount = events.filter(
      (event) => event.type === 'tab_switch'
    ).length;
    
    return {
      multipleFacesDetected: multipleFacesCount,
      tabChange: tabChangeCount,
    };
  }, [events]);

  return {
    status,
    events,
    clearEvents,
    getEvents,
    getCheatingEventCounts,
  };
};

