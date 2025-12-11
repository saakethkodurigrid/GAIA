import { API_BASE_URL } from '../utils/config';

// Type for API errors with status code
interface ApiError extends Error {
  status?: number;
  detail?: string;
}

const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
};

// Admin Job Response (includes recruiter_name for admin to see who created the job)
export interface AdminJobResponse {
  job_id: string;
  job_role: string;
  job_description: string;
  recruiter_email_id: string;
  recruiter_name: string;
  grade: string;
}

export interface ListJobsResponse {
  success: boolean;
  message: string;
  count: number;
  jobs: AdminJobResponse[];
}

/**
 * List all jobs in the system (Admin-only - sees all jobs from all recruiters)
 */
export const listJobs = async (): Promise<ListJobsResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/list-jobs`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to list jobs' }));
    const errorMessage = error.detail || 'Failed to list jobs';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
  }

  return response.json();
};

export interface InterviewResponse {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  job_id: string;
  job_role: string;
  recruiter_email: string;
  scheduled_date: string; // ISO format datetime string
  status: string; // 'shortlisted', 'rejected', 'scheduled', 'in progress', 'completed', 'selected', 'not selected'
}

export interface ListInterviewsResponse {
  success: boolean;
  message: string;
  count: number;
  interviews: InterviewResponse[];
}

/**
 * Get list of interviews scheduled for today (Admin-only - sees all interviews)
 */
export const listTodayInterviews = async (): Promise<ListInterviewsResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/list-interviews/today`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch interviews' }));
    const errorMessage = error.detail || 'Failed to fetch interviews';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
  }

  return response.json();
};

// Interview Analysis Types
export interface InterviewAnalysisResponse {
  success: boolean;
  message: string;
  candidate_id: string;
  mcq_analysis?: {
    score?: number;
    time_taken?: number;
    attempted?: {
      easy: number;
      medium: number;
      hard: number;
    };
    correct?: {
      easy: number;
      medium: number;
      hard: number;
    };
    total_questions?: number;
    [key: string]: unknown;
  } | null;
  coding_analysis?: {
    total_score?: number;
    time_taken?: number;
    total_submitted?: number;
    total_correct?: number;
    partially_correct?: number;
    total_questions?: number;
    [key: string]: unknown;
  } | null;
  system_design_analysis?: {
    score?: number;
    summary?: string;
    key_strengths?: string[];
    areas_of_improvement?: string[];
    suggested_learning?: string[];
    lowest_area?: string;
    things_to_improve?: string[];
    average_scores?: {
      [key: string]: number;
    };
    time_taken?: number;
    [key: string]: unknown;
  } | null;
  cheat_metrics?: {
    tab_change?: number;
    full_screen_exits?: number;
    multiple_face?: number;
    [key: string]: unknown;
  } | null;
  overall_percentage?: number | null;
  result?: 'PASS' | 'FAIL' | null;
  overall_summary?: string | null;
}

/**
 * Get interview analysis data for a specific candidate (Recruiter/Admin only)
 */
export const getInterviewAnalysis = async (candidateId: string): Promise<InterviewAnalysisResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/candidates/${candidateId}/interview-analysis`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch interview analysis' }));
    const errorMessage = error.detail || 'Failed to fetch interview analysis';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
  }

  return response.json();
};

