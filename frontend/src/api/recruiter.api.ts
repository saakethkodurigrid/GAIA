import { API_BASE_URL } from '../utils/config';

// Type for API errors with status code
interface ApiError extends Error {
  status?: number;
  detail?: string;
}

const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
};

export interface AddJobRequest {
  job_role: string;
  job_description: string;
  grade: string;
}

// Recruiter job response (includes recruiter_name from backend)
export interface RecruiterJobResponse {
  job_id: string;
  job_role: string;
  job_description: string;
  recruiter_email_id: string;
  recruiter_name: string;
  grade: string;
}

export interface AddJobResponse {
  success: boolean;
  message: string;
  data: RecruiterJobResponse | null;
}

export interface ListJobsResponse {
  success: boolean;
  message: string;
  count: number;
  jobs: RecruiterJobResponse[];
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

export interface CandidateEntry {
  name: string;
  email: string;
  file: File;
}

/**
 * Add a new job to the system (Recruiter endpoint)
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
    const errorMessage = error.detail || 'Failed to add job';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
  }

  return response.json();
};

/**
 * List all jobs for the current recruiter
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

/**
 * Upload multiple resume files (batch) for a job with candidate information
 * 
 * This function sends candidate data and resume files to the backend for batch processing.
 * The backend will:
 * 1. Extract text from resume files
 * 2. Scrub PII from resume text
 * 3. Calculate resume scores
 * 4. Create candidate records and assign them to the job
 * 
 * @param jobId - Job reference number in format JD-XXXXXX (e.g., JD-783901)
 * @param candidates - Array of candidate entries with name, email, and resume file
 * @returns Promise resolving to AddCandidatesBatchResponse with processing results
 * @throws Error if validation fails, authentication fails, or request fails
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

  // Validate jobId format (JD-XXXXXX)
  const jobIdPattern = /^JD-\d{6}$/;
  if (!jobIdPattern.test(jobId)) {
    throw new Error('Invalid job ID format. Expected format: JD-XXXXXX (e.g., JD-783901)');
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
    throw new Error(`Invalid file types. Only PDF, DOCX, and DOC are allowed. Invalid files: ${invalidFiles.join(', ')}`);
  }

  // Create FormData with files and candidate data
  const formData = new FormData();
  
  // Prepare candidates data as JSON array (matching backend expectation)
  // Backend expects: [{"name": "...", "email": "..."}, ...]
  const candidatesData = candidates.map(candidate => ({
    name: candidate.name.trim(),
    email: candidate.email.trim().toLowerCase()
  }));
  
  // Append candidates_data as JSON string (backend expects this field name)
  formData.append('candidates_data', JSON.stringify(candidatesData));
  
  // Append all files with field name "files" (must match backend parameter name)
  // Order must match candidates_data array (files[0] for candidate[0], etc.)
  candidates.forEach((candidate) => {
    formData.append('files', candidate.file);
  });

  try {
    const response = await fetch(`${API_BASE_URL}/admin/jobs/${jobId}/candidates/batch`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        // Don't set Content-Type header - browser will set it with boundary for FormData
      },
      body: formData,
    });

    // Parse response body (works for both success and error responses)
    const responseData = await response.json().catch(() => {
      // If JSON parsing fails, return a default error structure
      return { 
        success: false, 
        message: 'Failed to parse server response',
        detail: `Server returned status ${response.status}`
      };
    });

    // Handle error responses
    if (!response.ok) {
      // Backend may return 400 with AddCandidatesBatchResponse structure when all candidates fail
      // Check if it's a structured error response or a simple error detail
      if (responseData.detail) {
        throw new Error(responseData.detail);
      }
      if (responseData.message) {
        throw new Error(responseData.message);
      }
      throw new Error(`Failed to upload candidates: ${response.status} ${response.statusText}`);
    }

    // Return successful response
    return responseData as AddCandidatesBatchResponse;
  } catch (error) {
    // Re-throw if it's already an Error with a message
    if (error instanceof Error) {
      throw error;
    }
    // Otherwise wrap in Error
    throw new Error(`Failed to upload candidates: ${String(error)}`);
  }
};

// SSE Event Types
export interface SSEEvent {
  type: 'candidate' | 'error' | 'complete';
  data: CandidateBatchItemResponse | FailedFileResponse | { message: string } | { total: number; successful: number; failed: number };
}

export interface SSECandidateEvent {
  type: 'candidate';
  data: CandidateBatchItemResponse;
}

export interface SSEErrorEvent {
  type: 'error';
  data: FailedFileResponse | { message: string };
}

export interface SSECompleteEvent {
  type: 'complete';
  data: {
    total: number;
    successful: number;
    failed: number;
  };
}

/**
 * Upload multiple resume files with Server-Sent Events (SSE) streaming.
 * 
 * This function streams results as each candidate is processed, providing
 * real-time feedback to the user.
 * 
 * @param jobId - Job reference number in format JD-XXXXXX
 * @param candidates - Array of candidate entries with name, email, and resume file
 * @param onCandidate - Callback when a candidate is successfully processed
 * @param onError - Callback when a candidate fails or an error occurs
 * @param onComplete - Callback when all candidates are processed
 * @returns Promise that resolves when the stream is complete
 */
export const uploadCandidatesBatchStream = async (
  jobId: string,
  candidates: CandidateEntry[],
  onCandidate: (candidate: CandidateBatchItemResponse) => void,
  onError: (error: FailedFileResponse | { message: string }) => void,
  onComplete: (summary: { total: number; successful: number; failed: number }) => void
): Promise<void> => {
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

  // Validate jobId format
  const jobIdPattern = /^JD-\d{6}$/;
  if (!jobIdPattern.test(jobId)) {
    throw new Error('Invalid job ID format. Expected format: JD-XXXXXX (e.g., JD-783901)');
  }

  // Validate file types and required fields
  const allowedExtensions = ['pdf', 'docx', 'doc'];
  const invalidFiles: string[] = [];
  const missingFields: string[] = [];
  
  candidates.forEach((candidate, index) => {
    if (!candidate.name || candidate.name.trim() === '') {
      missingFields.push(`Candidate ${index + 1}: Name is required`);
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!candidate.email || !emailRegex.test(candidate.email)) {
      missingFields.push(`Candidate ${index + 1}: Valid email is required`);
    }
    
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
    throw new Error(`Invalid file types. Only PDF, DOCX, and DOC are allowed. Invalid files: ${invalidFiles.join(', ')}`);
  }

  // Create FormData
  const formData = new FormData();
  const candidatesData = candidates.map(candidate => ({
    name: candidate.name.trim(),
    email: candidate.email.trim().toLowerCase()
  }));
  
  formData.append('candidates_data', JSON.stringify(candidatesData));
  candidates.forEach((candidate) => {
    formData.append('files', candidate.file);
  });

  // Use fetch with POST to send form data
  // Note: We can't use EventSource for POST, so we'll use fetch with ReadableStream
  const response = await fetch(`${API_BASE_URL}/admin/jobs/${jobId}/candidates/batch-stream`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Don't set Content-Type - browser will set it with boundary
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to start upload stream' }));
    throw new Error(error.detail || error.message || 'Failed to start upload stream');
  }

  // Read the stream
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('Response body is not readable');
  }

  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      
      // Process complete SSE messages (lines ending with \n\n)
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.substring(6); // Remove 'data: ' prefix
            const event: SSEEvent = JSON.parse(jsonStr);
            
            switch (event.type) {
              case 'candidate':
                onCandidate(event.data as CandidateBatchItemResponse);
                break;
              case 'error':
                onError(event.data as FailedFileResponse | { message: string });
                break;
              case 'complete':
                onComplete(event.data as { total: number; successful: number; failed: number });
                break;
            }
          } catch (parseError) {
            console.error('Error parsing SSE event:', parseError);
            onError({ message: 'Failed to parse server response' });
          }
        }
      }
    }
    
    // Process any remaining buffer
    if (buffer.trim()) {
      const lines = buffer.split('\n\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.substring(6);
            const event: SSEEvent = JSON.parse(jsonStr);
            
            switch (event.type) {
              case 'candidate':
                onCandidate(event.data as CandidateBatchItemResponse);
                break;
              case 'error':
                onError(event.data as FailedFileResponse | { message: string });
                break;
              case 'complete':
                onComplete(event.data as { total: number; successful: number; failed: number });
                break;
            }
          } catch (parseError) {
            console.error('Error parsing SSE event:', parseError);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
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
    const errorMessage = error.detail || 'Failed to fetch resumes';
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
    const errorMessage = error.detail || 'Failed to fetch interviews';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
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
    const errorMessage = error.detail || 'Failed to fetch scheduled interviews';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
  }

  return response.json();
};

export interface CompletedInterviewCandidateResponse {
  candidate_id: string;
  name: string;
  email_id: string;
  resume_score: number | null;
  interview_score: number | null;
  status: string; // 'completed', 'selected', or 'not selected'
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
    const errorMessage = error.detail || 'Failed to fetch completed interviews';
    const apiError = new Error(errorMessage) as ApiError;
    apiError.status = response.status;
    apiError.detail = error.detail || errorMessage;
    throw apiError;
  }

  return response.json();
};

