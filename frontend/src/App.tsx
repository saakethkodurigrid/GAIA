import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { VideoProvider } from './context/VideoContext';
import { CheatingDetectionProvider } from './context/CheatingDetectionContext';
import HomePage from './app/HomePage';
import MCQPage from './app/Candidate/MCQPage';
import CodingTestPage from './app/Candidate/CodingTestPage';
import SystemDesignPage from './app/Candidate/SystemDesignPage';
import TourMCQPage from './app/tour/TourMCQPage';
import TourCodingPage from './app/tour/TourCodingPage';
import TourSystemDesignPage from './app/tour/TourSystemDesignPage';
import LoginPage from './app/Auth/LoginPage';
import CallbackPage from './app/Auth/CallbackPage';
import Admin from './pages/Admin';
import Recruiter from './pages/Recruiter';
import JobDetailsPage from './pages/JobDetailsPage';
import TestScheduledPage from './app/Candidate/TestScheduledPage';
import TestInstructionsPage from './app/Candidate/TestInstructionsPage';
import ScheduleInterviewPage from './app/Candidate/ScheduleInterviewPage';
import InterviewScheduledConfirmationPage from './app/Candidate/InterviewScheduledConfirmationPage';

import TestPermissionsPage from './app/Candidate/TestPermissionsPage';
import TestOverviewPage from './app/Candidate/TestOverviewPage';
import TestCompletedPage from './app/Candidate/TestCompletedPage';
import TestReadyPage from './app/Candidate/TestReadyPage';
import AnalysisPage from './app/Candidate/AnalysisPage';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated } = useAuth();
  const userData = localStorage.getItem('user_data');

  // Check if user is authenticated or has stored user data
  const isAuth = isAuthenticated || (userData !== null);

  if (!isAuth) {
    // Save the current URL (including query params) to redirect back after login
    const currentUrl = window.location.pathname + window.location.search;
    console.log('ProtectedRoute: User not authenticated, saving URL:', currentUrl);
    localStorage.setItem('redirect_after_login', currentUrl);
    return <Navigate to="/auth/login" replace />;
  }

  return children;
};

// Root route handler - redirects to login if not authenticated, otherwise based on user type
const RootRoute = () => {
  const { isAuthenticated, user } = useAuth();
  const userData = localStorage.getItem('user_data');
  const isAuth = isAuthenticated || (userData !== null);

  console.log('RootRoute triggered - isAuth:', isAuth, 'path:', window.location.pathname);

  if (isAuth) {
    // Get user type and status from context or localStorage
    let userType: string | undefined;
    let status: string | undefined;
    
    if (user?.userType) {
      userType = user.userType;
      status = user.status;
    } else if (userData) {
      try {
        const parsed = JSON.parse(userData);
        userType = parsed.userType;
        status = parsed.status;
      } catch {
        // Fallback to home if parsing fails
      }
    }

    console.log('RootRoute: userType:', userType, 'status:', status);

    // Redirect based on user type
    if (userType === 'admin') {
      console.log('RootRoute: Redirecting admin to /admin');
      return <Navigate to="/admin" replace />;
    }
    if (userType === 'recruiter') {
      console.log('RootRoute: Redirecting recruiter to /recruiter');
      return <Navigate to="/recruiter" replace />;
    }
    
    // For candidates, check if already scheduled
    if (userType === 'candidate') {
      // Check if there's a saved redirect with candidate_id
      const savedRedirect = localStorage.getItem('redirect_after_login');
      console.log('RootRoute: Saved redirect:', savedRedirect);
      
      if (savedRedirect) {
        const redirectPath = savedRedirect;
        console.log('RootRoute: Using saved redirect:', redirectPath);
        localStorage.removeItem('redirect_after_login');
        
        // If status is scheduled but URL has candidate_id, keep the candidate_id
        if (status === 'scheduled' && savedRedirect.includes('candidate_id')) {
          // Extract candidate_id from saved redirect
          const urlParams = new URLSearchParams(savedRedirect.split('?')[1] || '');
          const candidateId = urlParams.get('candidate_id');
          if (candidateId) {
            console.log('RootRoute: Redirecting to /test/scheduled with candidate_id');
            return <Navigate to={`/test/scheduled?candidate_id=${candidateId}`} replace />;
          }
        }
        
        return <Navigate to={redirectPath} replace />;
      }
      
      // Default redirects without saved URL
      if (status === 'scheduled') {
        console.log('RootRoute: Redirecting scheduled candidate to /test/scheduled');
        return <Navigate to="/test/scheduled" replace />;
      }
      
      console.log('RootRoute: No saved redirect, going to /schedule');
      return <Navigate to="/schedule" replace />;
    }
    
    // Default fallback - redirect to schedule
    console.log('RootRoute: Default redirect to /schedule');
    return <Navigate to="/schedule" replace />;
  }

  // Save the current URL if it has query params (for invitation links)
  const currentUrl = window.location.pathname + window.location.search;
  if (window.location.search) {
    console.log('RootRoute: Saving URL with query params:', currentUrl);
    localStorage.setItem('redirect_after_login', currentUrl);
  }

  console.log('RootRoute: Not authenticated, redirecting to /auth/login');
  return <Navigate to="/auth/login" replace />;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<CallbackPage />} />
      
      {/* Tutorial/Mock Test Pages - Public (no authentication required) */}
      <Route path="/tutorial/mcq" element={<TourMCQPage />} />
      <Route path="/tutorial/coding" element={<TourCodingPage />} />
      <Route path="/tutorial/system-design" element={<TourSystemDesignPage />} />
      
      {/* Root route - redirects based on auth status */}
      <Route path="/" element={<RootRoute />} />
      
      {/* Protected Routes - require authentication */}
      <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
      <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
      <Route path="/recruiter" element={<ProtectedRoute><Recruiter /></ProtectedRoute>} />
      <Route path="/recruiter/job-details" element={<ProtectedRoute><JobDetailsPage /></ProtectedRoute>} />
      <Route path="/schedule" element={<ProtectedRoute><ScheduleInterviewPage /></ProtectedRoute>} />
      <Route path="/interview/confirmed" element={<ProtectedRoute><InterviewScheduledConfirmationPage /></ProtectedRoute>} />
      <Route path="/test/scheduled" element={<ProtectedRoute><TestScheduledPage /></ProtectedRoute>} />
      <Route path="/test/instructions" element={<ProtectedRoute><TestInstructionsPage /></ProtectedRoute>} />
      <Route path="/test/ready" element={<ProtectedRoute><TestReadyPage /></ProtectedRoute>} />
      <Route path="/test/permissions" element={<ProtectedRoute><TestPermissionsPage /></ProtectedRoute>} />
      <Route
        path="/test-overview"
        element={
          <ProtectedRoute>
            <CheatingDetectionProvider enabled={true}>
              <TestOverviewPage />
            </CheatingDetectionProvider>
          </ProtectedRoute>
        }
      />
      <Route path="/test/completed" element={<ProtectedRoute><TestCompletedPage /></ProtectedRoute>} />
      <Route path="/candidate/analysis" element={<AnalysisPage />} />
      
      {/* Original Test Pages */}
      <Route
        path="/candidate/mcq"
        element={
          <ProtectedRoute>
            <CheatingDetectionProvider enabled={true}>
              <MCQPage />
            </CheatingDetectionProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/candidate/coding"
        element={
          <ProtectedRoute>
            <CheatingDetectionProvider enabled={true}>
              <CodingTestPage />
            </CheatingDetectionProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/candidate/system-design"
        element={
          <ProtectedRoute>
            <CheatingDetectionProvider enabled={true}>
              <SystemDesignPage />
            </CheatingDetectionProvider>
          </ProtectedRoute>
        }
      />
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <VideoProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </VideoProvider>
    </AuthProvider>
  );
}

export default App;
