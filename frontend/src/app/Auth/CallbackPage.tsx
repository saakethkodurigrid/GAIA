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
    // If already scheduled, redirect to scheduled page
    // if (status === 'scheduled') {
    //   console.log('Redirecting candidate to /test/scheduled (already scheduled)');
    //   return '/test/scheduled';
    // }
    // Otherwise, redirect to schedule page
    // console.log('Redirecting candidate to /schedule (not scheduled yet)');
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
        const state = searchParams.get('state');

        console.log('Callback page - authParam:', authParam ? 'present' : 'missing');
        console.log('Callback page - errorParam:', errorParam);
        console.log('Callback page - state:', state);

        // Verify state matches (CSRF protection)
        const storedState = localStorage.getItem('oauth_state');
        if (state && storedState && state !== storedState) {
          throw new Error('Invalid state parameter. Possible CSRF attack.');
        }

        // Clear OAuth state
        localStorage.removeItem('oauth_state');

        // Handle error from backend
        if (errorParam) {
          throw new Error(errorParam);
        }

        // Handle auth data from backend
        if (authParam) {
          try {
            // Decode base64 auth data
            const authJson = atob(authParam);
            const authResponse: AuthResponse = JSON.parse(authJson);
            
            console.log('Auth response:', authResponse);
            console.log('User type from response:', authResponse.user_type);
            console.log('Status from response:', authResponse.status);
            
            // Set auth state
            if (authContext.setAuthState) {
              authContext.setAuthState(authResponse);
            }

            // Redirect based on user type after successful login
            if (authResponse.success) {
              const redirectPath = getRedirectPath(authResponse.user_type, authResponse.status);
              console.log('Calculated redirect path:', redirectPath);
              console.log('User type used for redirect:', authResponse.user_type);
              // Use window.location for immediate redirect
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

