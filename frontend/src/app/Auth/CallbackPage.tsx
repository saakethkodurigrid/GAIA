import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { AuthResponse, AuthContextType, UserType, CandidateStatus } from '../../types';

interface AuthContextWithSetAuthState {
  setAuthState?: (authResponse: AuthResponse) => void;
}

/**
 * Determine redirect path based on user type and status
 */
const getRedirectPath = (userType?: UserType, status?: CandidateStatus): string => {
  console.log('getRedirectPath called with:', { userType, status });
  
  // Admin users -> /admin
  if (userType === 'admin') {
    console.log('Redirecting admin to /admin');
    return '/admin';
  }
  
  // Recruiter users -> /recruiter
  if (userType === 'recruiter') {
    console.log('Redirecting recruiter to /recruiter');
    return '/recruiter';
  }
  
  // Candidate users -> check status
  if (userType === 'candidate') {
    // If test is completed, redirect to completed page
    if (status === 'completed' || status === 'done') {
      console.log('Redirecting candidate to /test/completed (test completed)');
      return '/test/completed';
    }
    // If already scheduled, redirect to scheduled page
    if (status === 'scheduled') {
      console.log('Redirecting candidate to /test/scheduled (already scheduled)');
      return '/test/scheduled';
    }
    // Otherwise, redirect to schedule page
    console.log('Redirecting candidate to /schedule (not scheduled yet)');
    return '/schedule';
  }
  
  // Default fallback - redirect to /schedule
  console.log('No matching user type, defaulting to /schedule. userType was:', userType);
  return '/schedule';
};

const CallbackPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const authContext = useAuth() as AuthContextType & AuthContextWithSetAuthState;
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      try {
        const authParam = searchParams.get('auth');
        const errorParam = searchParams.get('error');
        const errorCode = searchParams.get('error_code');
        const state = searchParams.get('state');

        console.log('Callback page - authParam:', authParam ? 'present' : 'missing');
        console.log('Callback page - errorParam:', errorParam);
        console.log('Callback page - errorCode:', errorCode);
        console.log('Callback page - state:', state);

        // Verify state matches (CSRF protection)
        const storedState = localStorage.getItem('oauth_state');
        if (state && storedState) {
          try {
            // Try to parse stored state as JSON (if it contains candidate_id)
            const storedStateData = JSON.parse(atob(storedState));
            const stateData = JSON.parse(atob(state));
            
            // Compare CSRF tokens
            if (storedStateData.csrf !== stateData.csrf) {
              throw new Error('Invalid state parameter. Possible CSRF attack.');
            }
          } catch {
            // If not JSON, compare as plain strings (backward compatibility)
            if (state !== storedState) {
              throw new Error('Invalid state parameter. Possible CSRF attack.');
            }
          }
        }

        // Clear OAuth state
        localStorage.removeItem('oauth_state');

        // Handle error from backend
        if (errorParam) {
          const errorCode = searchParams.get('error_code');
          // Special handling for missing candidate_id
          if (errorCode === 'MISSING_CANDIDATE_ID') {
            setError('Candidate ID is required. Please access this page using the invitation link provided in your email.');
            setIsLoading(false);
            return;
          }
          throw new Error(errorParam);
        }

        // Handle auth data from backend
        if (authParam) {
          try {
            // Log the raw base64 encoded response from backend
            console.log('=== EXACT BACKEND RESPONSE (RAW) ===');
            console.log('Base64 Encoded Auth Param:', authParam);
            console.log('Length:', authParam.length);
            console.log('=====================================');
            
            // Decode base64 auth data
            const authJson = atob(authParam);
            console.log('=== EXACT BACKEND RESPONSE (DECODED JSON STRING) ===');
            console.log('Decoded JSON String:', authJson);
            console.log('====================================================');
            
            const authResponse: AuthResponse = JSON.parse(authJson);
            
            console.log('=== EXACT BACKEND RESPONSE (PARSED OBJECT) ===');
            console.log('Full Response Object:', JSON.stringify(authResponse, null, 2));
            console.log('');
            console.log('Field-by-Field Breakdown:');
            console.log('  success:', authResponse.success);
            console.log('  message:', authResponse.message);
            console.log('  user_type:', authResponse.user_type);
            console.log('  email:', authResponse.email);
            console.log('  name:', authResponse.name);
            console.log('  status:', authResponse.status);
            console.log('  candidate_id:', authResponse.candidate_id);
            console.log('  job_role:', authResponse.job_role);
            console.log('  redirect_url:', authResponse.redirect_url || 'not provided');
            console.log('  id_token:', authResponse.id_token ? `${authResponse.id_token.substring(0, 50)}...` : 'not provided');
            console.log('');
            console.log('=== CANDIDATE INFORMATION ===');
            console.log('Candidate Name:', authResponse.name || 'NOT PROVIDED');
            console.log('Job Role:', authResponse.job_role || 'NOT PROVIDED');
            console.log('===============================================');
            
            // Set auth state
            if (authContext.setAuthState) {
              authContext.setAuthState(authResponse);
            }

            // Redirect based on user type after successful login
            if (authResponse.success) {
              // Check if there's a saved redirect URL (for invitation links with candidate_id)
              const savedRedirect = localStorage.getItem('redirect_after_login');
              
              let redirectPath: string;
              if (savedRedirect) {
                console.log('CallbackPage: Found saved redirect URL:', savedRedirect);
                redirectPath = savedRedirect;
                
                // If saved redirect has candidate_id, make sure it's preserved
                if (savedRedirect.includes('candidate_id')) {
                  const urlParams = new URLSearchParams(savedRedirect.split('?')[1] || '');
                  const candidateId = urlParams.get('candidate_id');
                  if (candidateId) {
                    localStorage.setItem('current_candidate_id', candidateId);
                    console.log('CallbackPage: Stored candidate_id in localStorage:', candidateId);
                  }
                }
                
                // Clear the saved redirect
                localStorage.removeItem('redirect_after_login');
              } else {
                redirectPath = getRedirectPath(authResponse.user_type, authResponse.status);
                console.log('CallbackPage: Calculated redirect path:', redirectPath);
              }
              
              console.log('CallbackPage: User type used for redirect:', authResponse.user_type);
              console.log('CallbackPage: Final redirect path:', redirectPath);
              
              // Use window.location for immediate redirect to preserve query params
              window.location.href = redirectPath;
            } else {
              throw new Error(authResponse.message || 'Authentication failed');
            }
          } catch (decodeError) {
            const errorMsg = decodeError instanceof Error ? decodeError.message : 'Failed to decode authentication data';
            throw new Error(errorMsg);
          }
        } else {
          throw new Error('Missing authentication data. Make sure you are accessing this page through the OAuth flow.');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
        console.error('Callback error:', errorMessage);
        setError(errorMessage);
        setIsLoading(false);
      }
    };

    processCallback();
  }, [searchParams, navigate, authContext]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Completing authentication...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-12 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Authentication Failed</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/auth/login')}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default CallbackPage;

