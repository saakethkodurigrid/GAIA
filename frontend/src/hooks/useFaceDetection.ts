import { useEffect, useRef } from 'react';
import { loadModels, detectFaces, logMultipleFaces } from '../utils/faceDetection';

/**
 * Hook to detect multiple faces from a video element and log to localStorage
 */
export const useFaceDetection = (
  videoElement: HTMLVideoElement | null,
  enabled: boolean = true
) => {
  const detectionIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastFaceCountRef = useRef<number>(0);
  const modelsLoadedRef = useRef<boolean>(false);

  useEffect(() => {
    console.log('[Face Detection Hook] Effect triggered', { enabled, hasVideoElement: !!videoElement });
    
    if (!enabled) {
      console.log('[Face Detection Hook] Detection disabled');
      return;
    }
    
    if (!videoElement) {
      console.log('[Face Detection Hook] No video element available');
      return;
    }

    let isMounted = true;

    const initializeDetection = async () => {
      try {
        // Load models if not already loaded
        if (!modelsLoadedRef.current) {
          await loadModels();
          modelsLoadedRef.current = true;
        }

        // Wait for video to be ready and playing
        const checkVideoReady = () => {
          if (!isMounted || !videoElement) {
            console.log('[Face Detection] Video element not available');
            return;
          }
          
          const isReady = videoElement.readyState >= 2;
          const hasDimensions = videoElement.videoWidth > 0 && videoElement.videoHeight > 0;
          const isPlaying = !videoElement.paused && !videoElement.ended;
          
          console.log('[Face Detection] Checking video readiness', {
            readyState: videoElement.readyState,
            videoWidth: videoElement.videoWidth,
            videoHeight: videoElement.videoHeight,
            isPlaying,
            isReady,
            hasDimensions,
          });
          
          if (isReady && hasDimensions && isPlaying) {
            // Video is ready, start detection
            console.log('[Face Detection] Video is ready, starting detection');
            startDetection();
          } else {
            // Wait a bit and check again
            setTimeout(checkVideoReady, 200);
          }
        };

        const startDetection = () => {
          if (!isMounted || !videoElement) return;

          // Clear any existing interval
          if (detectionIntervalRef.current) {
            clearInterval(detectionIntervalRef.current);
          }

          // Start detection loop
          detectionIntervalRef.current = setInterval(async () => {
            if (!isMounted || !videoElement) {
              return;
            }
            
            // Check if video is ready
            if (videoElement.readyState < 2) {
              console.log('[Face Detection] Video not ready, skipping detection');
              return;
            }
            
            if (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
              console.log('[Face Detection] Video has no dimensions, skipping detection');
              return;
            }

            try {
              console.log('[Face Detection] Starting face detection...');
              const faceCount = await detectFaces(videoElement);
              
              // Log all detections for debugging (including single faces and zero)
              console.log(`[Face Detection] ✅ Detected ${faceCount} face(s)`, {
                videoWidth: videoElement.videoWidth,
                videoHeight: videoElement.videoHeight,
                readyState: videoElement.readyState,
                playing: !videoElement.paused,
                currentTime: videoElement.currentTime,
                previousCount: lastFaceCountRef.current,
              });
              
              // Log to localStorage when face count changes and is > 1
              if (faceCount > 1) {
                if (faceCount !== lastFaceCountRef.current) {
                  console.log(`[Face Detection] ⚠️ Multiple faces detected: ${faceCount} - Logging to localStorage`);
                  logMultipleFaces(faceCount);
                }
                lastFaceCountRef.current = faceCount;
              } else {
                // Reset when face count goes back to 0 or 1
                if (lastFaceCountRef.current > 1) {
                  console.log(`[Face Detection] Face count returned to normal (${faceCount} face)`);
                }
                lastFaceCountRef.current = faceCount;
              }
            } catch (error) {
              console.error('[Face Detection] ❌ Error in face detection loop:', error);
            }
          }, 15000); // Check every 15 seconds
        };

        checkVideoReady();
      } catch (error) {
        console.error('Error initializing face detection:', error);
      }
    };

    initializeDetection();

    return () => {
      isMounted = false;
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }
    };
  }, [enabled, videoElement]);
};

