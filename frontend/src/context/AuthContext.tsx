import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { getGoogleAuthURL } from '../api/auth.api';
import type { AuthContextType, AuthResponse } from '../types';

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
      // Generate a random state for CSRF protection
      const state = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
      localStorage.setItem('oauth_state', state);
      
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
    localStorage.removeItem('user_data');
    localStorage.removeItem('mcq_answers'); // Clear MCQ answers on logout
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
      setUser({
        email: authResponse.email,
        name: authResponse.name,
        userType: authResponse.user_type,
        status: authResponse.status,
        candidateId: authResponse.candidate_id,
      });
      // Store user data in localStorage
      localStorage.setItem('user_data', JSON.stringify({
        email: authResponse.email,
        name: authResponse.name,
        userType: authResponse.user_type,
        status: authResponse.status,
        candidateId: authResponse.candidate_id,
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

