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

