import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { getGoogleAuthURL } from '../api/auth.api';
import type { AuthContextType, AuthResponse } from '../types';
import { localStorage as storage } from '../utils/localStorage';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  // Initialize auth state from localStorage
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const userData = localStorage.getItem('user_data');
    return userData !== null;
  });

  
  const [user, setUser] = useState<AuthContextType['user']>(() => {
    const userData = localStorage.getItem('user_data');
    if (userData) {
      try {
        return JSON.parse(userData);
      } catch {
        return null;
      }
    }
    return null;
  });


  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Get candidate_id from localStorage if available (from scheduling link)
      const candidateId = localStorage.getItem('current_candidate_id');
      
      let state: string;
      if (candidateId) {
        // Encode candidate_id in state parameter (for scheduling links)
        const stateData = {
          csrf: Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
          candidate_id: candidateId
        };
        state = btoa(JSON.stringify(stateData));
        localStorage.setItem('oauth_state', state);
        console.log('Login: Including candidate_id in OAuth state:', candidateId);
      } else {
        // Check if user is trying to access a candidate route
        const currentPath = window.location.pathname;
        const candidateRoutes = ['/schedule', '/test/', '/candidate/'];
        const isCandidateRoute = candidateRoutes.some(route => currentPath.includes(route));
        
        if (isCandidateRoute) {
          // Block login for candidate routes without candidate_id
          setError('Candidate ID is required. Please access this page using the invitation link provided in your email.');
          setIsLoading(false);
          return;
        }
        
        // Generate a random state for CSRF protection (for admin/recruiter)
        state = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('oauth_state', state);
      }
      
      // Get Google OAuth URL
      const response = await getGoogleAuthURL(state);
      
      // Redirect to Google OAuth
      window.location.href = response.auth_url;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to initiate login';
      setError(errorMessage);
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setIsAuthenticated(false);
    setUser(null);
    localStorage.removeItem('oauth_state');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('google_id_token');
    localStorage.removeItem('user_data');
    localStorage.removeItem('redirect_after_login');
    localStorage.removeItem('current_candidate_id');
    // Clear all test-related data
    localStorage.removeItem('mcq_answers');
    localStorage.removeItem('submitted_sections');
    // Clear any other test-related localStorage items
    // Note: This ensures a clean slate when user logs out
    // Redirect to login page after logout
    window.location.href = '/auth/login';
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Function to set auth state after successful login (called from callback page)
  const setAuthState = useCallback((authResponse: AuthResponse) => {
    console.log('Login data from backend:', authResponse);
    setIsAuthenticated(authResponse.success);
    if (authResponse.success) {
      // Check if candidate_id has changed and flush test data if needed
      if (authResponse.candidate_id) {
        storage.checkAndFlushOnCandidateChange(authResponse.candidate_id);
        // Store candidate_id in localStorage
        localStorage.setItem('current_candidate_id', authResponse.candidate_id);
      }
      
      setUser({
        email: authResponse.email,
        name: authResponse.name,
        userType: authResponse.user_type,
        status: authResponse.status,
        candidateId: authResponse.candidate_id,
        jobRole: authResponse.job_role,
      });
      // Store user data in localStorage
      localStorage.setItem('user_data', JSON.stringify({
        email: authResponse.email,
        name: authResponse.name,
        userType: authResponse.user_type,
        status: authResponse.status,
        candidateId: authResponse.candidate_id,
        jobRole: authResponse.job_role,
      }));
      
      // Store Google ID token for API authentication
      if (authResponse.id_token) {
        localStorage.setItem('auth_token', authResponse.id_token);
        localStorage.setItem('google_id_token', authResponse.id_token);
      }
    }
    setIsLoading(false);
  }, []);

  const value: AuthContextType = {
    isAuthenticated,
    user,
    isLoading,
    error,
    login,
    logout,
    clearError,
  };

  return (
    <AuthContext.Provider value={{ ...value, setAuthState } as AuthContextType & { setAuthState: typeof setAuthState }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

