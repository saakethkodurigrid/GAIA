import { API_BASE_URL } from '../utils/config';

const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
};

export interface AddJobRequest {
  job_role: string;
  job_description: string;
  grade: string;
}

export interface JobResponse {
  job_id: string;
  job_role: string;
  job_description: string;
  recruiter_email_id: string;
  grade: string;
}

export interface AddJobResponse {
  success: boolean;
  message: string;
  data: JobResponse | null;
}

export interface ListJobsResponse {
  success: boolean;
  message: string;
  count: number;
  jobs: JobResponse[];
}

export interface CandidateBatchItemResponse {
  candidate_id: string;
  name: string;
  email_id: string;
  status: string;
  resume_score: number;
  processing_status: string;
  errors?: string | null;
}

export interface FailedFileResponse {
  filename: string;
  error: string;
}

export interface AddCandidatesBatchResponse {
  success: boolean;
  message: string;
  total_files: number;
  successful: number;
  failed: number;
  candidates: CandidateBatchItemResponse[];
  failed_files: FailedFileResponse[];
}

/**
 * Add a new job to the system
 */
export const addJob = async (request: AddJobRequest): Promise<AddJobResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/add-job`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to add job' }));
    throw new Error(error.detail || 'Failed to add job');
  }

 

  return response.json();
};

/**
 * List all jobs in the system
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
    throw new Error(error.detail || 'Failed to list jobs');
  }

  return response.json();
};

export interface CandidateEntry {
  name: string;
  email: string;
  file: File;
}

/**
 * Upload multiple resume files (batch) for a job with candidate information
 */
export const uploadCandidatesBatch = async (
  jobId: string,
  candidates: CandidateEntry[]
): Promise<AddCandidatesBatchResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  // Validate candidate count
  if (candidates.length === 0) {
    throw new Error('At least one candidate is required');
  }

  if (candidates.length > 10) {
    throw new Error('Maximum 10 candidates allowed');
  }

  // Validate file types and required fields
  const allowedExtensions = ['pdf', 'docx', 'doc'];
  const invalidFiles: string[] = [];
  const missingFields: string[] = [];
  
  candidates.forEach((candidate, index) => {
    // Validate name
    if (!candidate.name || candidate.name.trim() === '') {
      missingFields.push(`Candidate ${index + 1}: Name is required`);
    }
    
    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!candidate.email || !emailRegex.test(candidate.email)) {
      missingFields.push(`Candidate ${index + 1}: Valid email is required`);
    }
    
    // Validate file
    if (!candidate.file) {
      missingFields.push(`Candidate ${index + 1}: Resume file is required`);
    } else {
      const extension = candidate.file.name.toLowerCase().split('.').pop() || '';
      if (!allowedExtensions.includes(extension)) {
        invalidFiles.push(candidate.file.name);
      }
    }
  });

  if (missingFields.length > 0) {
    throw new Error(`Missing required fields: ${missingFields.join('; ')}`);
  }

  if (invalidFiles.length > 0) {
    throw new Error(`Invalid file types. Only PDF and DOCX are allowed. Invalid files: ${invalidFiles.join(', ')}`);
  }

  // Create FormData with files and candidate data
  const formData = new FormData();
  
  // Prepare candidates data as JSON array (matching backend expectation)
  const candidatesData = candidates.map(candidate => ({
    name: candidate.name.trim(),
    email: candidate.email.trim().toLowerCase()
  }));
  
  // Append candidates_data as JSON string
  formData.append('candidates_data', JSON.stringify(candidatesData));
  
  // Append all files (order must match candidates_data array)
  candidates.forEach((candidate) => {
    formData.append('files', candidate.file);
  });

  const response = await fetch(`${API_BASE_URL}/admin/jobs/${jobId}/candidates/batch`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to upload resumes' }));
    throw new Error(error.detail || 'Failed to upload resumes');
  }

  return response.json();
};

export interface ResumeCandidateResponse {
  candidate_id: string;
  name: string;
  email_id: string;
  resume_score: number;
  status: string; // 'shortlisted' or 'rejected'
}

export interface ResumesListResponse {
  success: boolean;
  message: string;
  count: number;
  candidates: ResumeCandidateResponse[];
}

/**
 * Get list of all candidates for resumes view
 */
export const getResumesList = async (jobId: string): Promise<ResumesListResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/jobs/${jobId}/candidates/resumes`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch resumes' }));
    throw new Error(error.detail || 'Failed to fetch resumes');
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
 * Get list of interviews scheduled for today
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
    throw new Error(error.detail || 'Failed to fetch interviews');
  }

  return response.json();
};

export interface ScheduledInterviewCandidateResponse {
  candidate_id: string;
  name: string;
  email_id: string;
  interview_status: string; // 'shortlisted', 'scheduled', 'in progress', 'completed', 'selected', 'not selected'
  interview_date: string | null; // ISO format datetime string
}

export interface ScheduledInterviewsListResponse {
  success: boolean;
  message: string;
  count: number;
  candidates: ScheduledInterviewCandidateResponse[];
}

/**
 * Get list of scheduled interviews for a job
 */
export const getScheduledInterviews = async (jobId: string): Promise<ScheduledInterviewsListResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/jobs/${jobId}/candidates/scheduled-interviews`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch scheduled interviews' }));
    throw new Error(error.detail || 'Failed to fetch scheduled interviews');
  }

  return response.json();
};

export interface CompletedInterviewCandidateResponse {
  candidate_id: string;
  name: string;
  email_id: string;
  interview_score: number | null;
  status: string; // 'selected' or 'not selected'
  report_link: string | null;
}

export interface CompletedInterviewsListResponse {
  success: boolean;
  message: string;
  count: number;
  candidates: CompletedInterviewCandidateResponse[];
}

/**
 * Get list of completed interviews for a job
 */
export const getCompletedInterviews = async (jobId: string): Promise<CompletedInterviewsListResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(`${API_BASE_URL}/admin/jobs/${jobId}/candidates/completed-interviews`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch completed interviews' }));
    throw new Error(error.detail || 'Failed to fetch completed interviews');
  }

  return response.json();
};

