import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useVideo } from '../../context/VideoContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import VideoPreview from '../../components/VideoPreview/VideoPreview';

const TestPermissionsPage = () => {
  const { user, logout } = useAuth();
  const { videoStream: globalVideoStream, setVideoStream: setGlobalVideoStream, requestVideoStream } = useVideo();
  const navigate = useNavigate();
  const [cameraPermission, setCameraPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [fullscreenPermission, setFullscreenPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [localVideoStream, setLocalVideoStream] = useState<MediaStream | null>(null);
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [showPhotoPreview, setShowPhotoPreview] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    checkPermissions();
  }, []);

  const checkPermissions = async () => {
    try {
      // Check if camera is available (but don't request access yet)
      // enumerateDevices may not return device labels without permission, but will still return devices
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const hasVideoInput = devices.some(device => device.kind === 'videoinput');
        setCameraPermission(hasVideoInput ? 'prompt' : 'denied');
      } catch {
        // If enumerateDevices fails, assume camera might be available
        setCameraPermission('prompt');
      }

      // Check fullscreen availability
      if (document.fullscreenEnabled) {
        setFullscreenPermission('prompt');
      } else {
        setFullscreenPermission('denied');
      }
    } catch {
      setError('Failed to check permissions. Please ensure your browser supports media access.');
      setCameraPermission('denied');
    } finally {
      setIsChecking(false);
    }
  };

  const requestCamera = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      setLocalVideoStream(stream);
      setShowCameraModal(true);
    } catch (err) {
      console.error('Camera error:', err);
      setError('Failed to enable camera. Please allow camera access to continue.');
      setCameraPermission('denied');
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      if (context) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to base64 image
        const photoData = canvas.toDataURL('image/png');
        setCapturedPhoto(photoData);
        
        // Store video stream globally for use in test pages
        if (localVideoStream) {
          setGlobalVideoStream(localVideoStream);
        }
        
        // Close camera modal and show photo preview
        setShowCameraModal(false);
        setShowPhotoPreview(true);
      }
    }
  };

  const retakePhoto = async () => {
    setCapturedPhoto(null);
    setShowPhotoPreview(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      setLocalVideoStream(stream);
      setShowCameraModal(true);
    } catch (err) {
      console.error('Camera error:', err);
      setError('Failed to access camera. Please try again.');
    }
  };

  // Set video stream when modal opens and stream is available
  useEffect(() => {
    if (showCameraModal && localVideoStream && videoRef.current) {
      videoRef.current.srcObject = localVideoStream;
      videoRef.current.play().catch(err => {
        console.error('Error playing video:', err);
      });
    }
  }, [showCameraModal, localVideoStream]);

  const requestFullscreen = async () => {
    try {
      setError(null);
      const element = document.documentElement;
      const requestMethod = 
        element.requestFullscreen ||
        (element as HTMLElement & { webkitRequestFullscreen?: () => Promise<void> }).webkitRequestFullscreen ||
        (element as HTMLElement & { mozRequestFullScreen?: () => Promise<void> }).mozRequestFullScreen ||
        (element as HTMLElement & { msRequestFullscreen?: () => Promise<void> }).msRequestFullscreen;

      if (requestMethod) {
        await requestMethod.call(element);
        setFullscreenPermission('granted');
      } else {
        setFullscreenPermission('denied');
        setError('Fullscreen is not supported in your browser.');
      }
    } catch {
      setError('Failed to enable fullscreen. Please allow fullscreen access to continue.');
      setFullscreenPermission('denied');
    }
  };

  const handleJoinInterview = () => {
    if (cameraPermission === 'granted' && fullscreenPermission === 'granted' && consentChecked) {
      // Navigate to instructions page after permissions are granted
      navigate('/test/instructions');
    }
  };

  const handleLogout = () => {
    logout();
  };

  const allPermissionsGranted = capturedPhoto !== null && fullscreenPermission === 'granted' && consentChecked;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] relative overflow-hidden">
      {/* Header */}
      <Header showUserInfo={true} showLogout={true} showTechInterviewLogo={true} user={user} onLogout={handleLogout} />

      {/* Main Content */}
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] py-8">
        <div className="w-full max-w-5xl px-4">
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-yellow-400 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
              </svg>
            </div>
          </div>

          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-3">Ready to Start Your Interview?</h1>
            <p className="text-lg text-gray-600">Before we begin, we need to set up your camera and screen</p>
          </div>

          {/* Two Cards Side by Side */}
          <div className="flex gap-6 mb-8 justify-center">
            {/* Camera Access Card */}
            <div className="flex-1 max-w-md bg-white rounded-xl shadow-lg border-2 border-gray-200 p-6">
              <div className="flex flex-col items-center text-center mb-4">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Camera Access</h3>
                <p className="text-sm text-gray-600 mb-4">Required for video interview and photo identification</p>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-gray-700 text-center">Click below to allow camera access</p>
              </div>

              <button
                onClick={requestCamera}
                disabled={capturedPhoto !== null || isChecking}
                className={`w-full py-3 px-6 rounded-lg font-semibold text-base transition-colors ${
                  capturedPhoto !== null
                    ? 'bg-green-500 text-white cursor-not-allowed'
                    : 'bg-yellow-500 text-white hover:bg-yellow-600'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {capturedPhoto !== null ? 'Photo Captured' : 'Enable Camera'}
              </button>
            </div>

            {/* Full Screen Access Card */}
            <div className="flex-1 max-w-md bg-white rounded-xl shadow-lg border-2 border-gray-200 p-6">
              <div className="flex flex-col items-center text-center mb-4">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Full Screen Access</h3>
                <p className="text-sm text-gray-600 mb-4">Required for a secure testing environment</p>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-gray-700 text-center">Click below to allow full screen access</p>
              </div>

              <button
                onClick={requestFullscreen}
                disabled={fullscreenPermission === 'granted' || isChecking}
                className={`w-full py-3 px-6 rounded-lg font-semibold text-base transition-colors ${
                  fullscreenPermission === 'granted'
                    ? 'bg-green-500 text-white cursor-not-allowed'
                    : 'bg-yellow-500 text-white hover:bg-yellow-600'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {fullscreenPermission === 'granted' ? 'Full Screen Enabled' : 'Enable Full Screen'}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 max-w-2xl mx-auto">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          )}

          {/* Consent Checkbox */}
          <div className="flex items-start gap-3 mb-8 max-w-2xl mx-auto">
            <input
              type="checkbox"
              id="consent"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              className="mt-1 w-5 h-5 text-yellow-500 border-gray-300 rounded focus:ring-yellow-500"
            />
            <label htmlFor="consent" className="text-sm text-gray-700 cursor-pointer">
              I understand and consent to being recorded during this interview. I acknowledge that the recording will be reviewed and accessed by the HR team and hiring managers for evaluation purposes.
            </label>
          </div>

          {/* Join Interview Button */}
          <div className="flex justify-center">
            <button
              onClick={handleJoinInterview}
              disabled={!allPermissionsGranted}
              className={`px-12 py-4 rounded-lg font-semibold text-lg transition-colors ${
                allPermissionsGranted
                  ? 'bg-gray-900 text-white hover:bg-gray-800'
                  : 'bg-gray-400 text-gray-200 cursor-not-allowed'
              }`}
            >
              Start Tour
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />

      {/* Camera Modal */}
      {showCameraModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full mx-4">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Camera Permissions</h2>
            </div>
            
            {/* Camera Feed */}
            <div className="p-6">
              <div className="relative bg-gray-900 rounded-lg overflow-hidden mb-4" style={{ width: '100%', height: '500px', minHeight: '400px' }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      videoRef.current.play().catch(err => {
                        console.error('Error playing video:', err);
                      });
                    }
                  }}
                />
              </div>
              
              <p className="text-sm text-gray-700 mb-4 text-center">
                Confirm camera setup and capture photo
              </p>
              
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    if (localVideoStream) {
                      localVideoStream.getTracks().forEach(track => track.stop());
                      setLocalVideoStream(null);
                    }
                    setShowCameraModal(false);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={capturePhoto}
                  className="px-6 py-2 text-sm font-medium text-white bg-orange-500 rounded-md hover:bg-orange-600 transition-colors"
                >
                  OK
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Captured Photo Preview */}
      {capturedPhoto && showPhotoPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Photo Captured</h2>
            </div>
            
            <div className="p-6">
              <div className="relative bg-gray-900 rounded-lg overflow-hidden mb-4" style={{ width: '100%', height: '500px', minHeight: '400px' }}>
                <img
                  src={capturedPhoto}
                  alt="Captured photo"
                  className="w-full h-full object-cover"
                />
              </div>
              
              <div className="flex justify-end gap-3">
                <button
                  onClick={retakePhoto}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Retake
                </button>
                <button
                  onClick={async () => {
                    // TODO: Send photo to backend
                    // For now, just store it and close the preview
                    // The photo is already stored in capturedPhoto state
                    // In the future, you can send it like this:
                    // await sendPhotoToBackend(capturedPhoto);
                    // Example API call:
                    // const formData = new FormData();
                    // const blob = await fetch(capturedPhoto).then(r => r.blob());
                    // formData.append('photo', blob, 'photo.png');
                    // await fetch('/api/upload-photo', { method: 'POST', body: formData });
                    setCameraPermission('granted');
                    setShowPhotoPreview(false);
                  }}
                  className="px-6 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 transition-colors"
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hidden canvas for capturing photo */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Video Preview Component - Show after camera permission is granted */}
      {capturedPhoto !== null && (
        <VideoPreview 
          videoStream={globalVideoStream} 
          onStreamRequest={requestVideoStream}
        />
      )}
    </div>
  );
};

export default TestPermissionsPage;
