import * as faceapi from '@vladmandic/face-api';

let modelsLoaded = false;
const FACE_DETECTION_LOGS_KEY = 'face_detection_logs';

export interface FaceDetectionLog {
  timestamp: number;
  faceCount: number;
  message: string;
}

/**
 * Load face detection models
 */
export const loadModels = async (): Promise<void> => {
  if (modelsLoaded) return;
  
  try {
    // Try loading from local /models first, fallback to CDN
    try {
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri('/models'),
        faceapi.nets.faceLandmark68Net.loadFromUri('/models'),
      ]);
      modelsLoaded = true;
      console.log('Face detection models loaded successfully from local /models');
    } catch (localError) {
      console.warn('Failed to load models from local /models, trying CDN...', localError);
      // Fallback to CDN
      const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model';
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
      ]);
      modelsLoaded = true;
      console.log('Face detection models loaded successfully from CDN');
    }
  } catch (error) {
    console.error('Error loading face detection models:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    if (errorMessage.includes('404') || errorMessage.includes('Failed to fetch') || errorMessage.includes('JSON')) {
      throw new Error('Face detection models not found. Please ensure models are downloaded to /public/models/ or check your internet connection for CDN fallback.');
    }
    throw error;
  }
};

/**
 * Detect faces in video element
 */
export const detectFaces = async (videoElement: HTMLVideoElement): Promise<number> => {
  if (!modelsLoaded) {
    console.warn('[Face Detection] Models not loaded yet');
    return 0;
  }
  
  if (!videoElement) {
    console.warn('[Face Detection] Video element not provided');
    return 0;
  }

  // Check if video has valid dimensions
  if (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
    console.warn('[Face Detection] Video has no dimensions');
    return 0;
  }

  try {
    // Use TinyFaceDetectorOptions with better settings for webcam
    const options = new faceapi.TinyFaceDetectorOptions({
      inputSize: 416, // Larger input size for better detection
      scoreThreshold: 0.5, // Lower threshold to detect more faces
    });

    const detections = await faceapi
      .detectAllFaces(videoElement, options)
      .withFaceLandmarks();

    console.log(`[Face Detection] Raw detection result: ${detections.length} face(s) found`);
    
    return detections.length;
  } catch (error) {
    console.error('[Face Detection] Error detecting faces:', error);
    if (error instanceof Error) {
      console.error('[Face Detection] Error details:', error.message, error.stack);
    }
    return 0;
  }
};

/**
 * Log multiple face detection to localStorage
 */
export const logMultipleFaces = (faceCount: number): void => {
  if (faceCount <= 1) return; // Only log when more than 1 face

  const log: FaceDetectionLog = {
    timestamp: Date.now(),
    faceCount,
    message: `Multiple faces detected: ${faceCount} faces`,
  };

  try {
    const existingLogs = getFaceDetectionLogs();
    existingLogs.push(log);
    
    // Keep only last 1000 logs to prevent localStorage overflow
    const logsToStore = existingLogs.slice(-1000);
    window.localStorage.setItem(FACE_DETECTION_LOGS_KEY, JSON.stringify(logsToStore));
  } catch (error) {
    console.error('Error logging face detection:', error);
  }
};

/**
 * Get all face detection logs from localStorage
 */
export const getFaceDetectionLogs = (): FaceDetectionLog[] => {
  try {
    const stored = window.localStorage.getItem(FACE_DETECTION_LOGS_KEY);
    if (stored) {
      return JSON.parse(stored) as FaceDetectionLog[];
    }
  } catch (error) {
    console.error('Error reading face detection logs from localStorage:', error);
  }
  return [];
};

/**
 * Clear face detection logs
 */
export const clearFaceDetectionLogs = (): void => {
  try {
    window.localStorage.removeItem(FACE_DETECTION_LOGS_KEY);
  } catch (error) {
    console.error('Error clearing face detection logs:', error);
  }
};

