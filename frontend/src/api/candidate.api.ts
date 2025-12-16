import { API_BASE_URL } from '../utils/config';

export interface ScheduleTestRequest {
  scheduled_date: string; // ISO format datetime string
}

export interface ScheduleTestResponse {
  success: boolean;
  message: string;
  scheduled_date: string | null; // ISO format datetime string
}

export interface GetScheduledDateResponse {
  success: boolean;
  message: string;
  scheduled_date: string | null; // ISO format datetime string with timezone
}

/**
 * Convert a Date object to IST (Indian Standard Time) format
 * Treats the date/time as IST time and formats it with +05:30 offset
 * IST is UTC+5:30
 */
const toISTString = (date: Date): string => {
  // The date parameter represents a time selected by the user in their local timezone.
  // However, we need to interpret the selected time as IST time for storage.
  // Extract the date/time components and treat them as IST components.
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  // Create an ISO string with IST offset, treating the extracted components as IST time
  // This ensures that when the user selects "10 AM", it's stored as "10 AM IST"
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}+05:30`;
};

/**
 * Schedule a test for the authenticated candidate
 */
export const scheduleTest = async (
  scheduledDate: Date,
  token: string,
  candidateId: string
): Promise<ScheduleTestResponse> => {
  // Convert date to IST format string
  const scheduledDateISO = toISTString(scheduledDate);
  
  // Validate candidateId
  if (!candidateId) {
    throw new Error('Candidate ID is required. Please login again.');
  }
  
  const requestPayload = {
    scheduled_date: scheduledDateISO,
  };
  
  // Log exact payload being sent to backend
  console.log('Schedule API Payload:', JSON.stringify(requestPayload));
  
  const response = await fetch(
    `${API_BASE_URL}/candidate/schedule-test?candidate_id=${encodeURIComponent(candidateId)}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(requestPayload as ScheduleTestRequest),
    }
  );

  // Log response
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to schedule test' }));
    console.log('Schedule API Response:', error);
    throw new Error(error.detail || 'Failed to schedule test');
  }

  const responseData = await response.json();
  console.log('Schedule API Response:', responseData);
  
  return responseData;
};

/**
 * Get the scheduled date for a candidate
 * Fetches the scheduled_date directly from the backend to avoid timezone conversion issues
 */
export const getScheduledDate = async (
  candidateId: string,
  token?: string
): Promise<GetScheduledDateResponse> => {
  // Validate candidateId
  if (!candidateId) {
    throw new Error('Candidate ID is required. Please access this page using the invitation link.');
  }

  // Use provided token or get from localStorage
  const finalToken = token || getAuthToken();
  if (!finalToken) {
    throw new Error('Authentication token not found. Please login again.');
  }

  console.log('=== getScheduledDate API Call ===');
  console.log('URL:', `${API_BASE_URL}/candidate/${candidateId}/scheduled-date`);
  console.log('Candidate ID:', candidateId);
  
  const response = await fetch(
    `${API_BASE_URL}/candidate/${candidateId}/scheduled-date`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${finalToken}`,
      },
    }
  );

  console.log('Response Status:', response.status);
  console.log('Response OK:', response.ok);
  console.log('Response Headers:', Object.fromEntries(response.headers.entries()));

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to get scheduled date' }));
    console.error('API Error Response:', error);
    throw new Error(error.detail || 'Failed to get scheduled date');
  }

  const responseData = await response.json();
  console.log('API Success Response:', JSON.stringify(responseData, null, 2));
  console.log('===============================');
  
  return responseData;
};

// Get auth token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
};

// Get candidate_id from localStorage
const getCandidateId = (): string | null => {
  return localStorage.getItem('current_candidate_id');
};

export interface UploadImageResponse {
  blob_url: string;
  filename: string;
  candidate_id: string;
}

/**
 * Upload a candidate photo/image
 * @param candidateId - The candidate's UUID
 * @param imageDataUrl - Base64 data URL of the image (e.g., from canvas.toDataURL())
 * @returns Upload result with blob URL
 */
export const uploadCandidateImage = async (
  candidateId: string,
  imageDataUrl: string
): Promise<UploadImageResponse> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  if (!candidateId) {
    throw new Error('Candidate ID is required.');
  }

  // Convert base64 data URL to blob (without using fetch to avoid CSP issues)
  // Format: data:image/png;base64,iVBORw0KGgo...
  let blob: Blob;
  try {
    // Extract base64 data from data URL
    const base64Data = imageDataUrl.split(',')[1];
    if (!base64Data) {
      throw new Error('Invalid data URL format');
    }
    
    // Convert base64 to binary
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Determine MIME type from data URL
    const mimeMatch = imageDataUrl.match(/data:([^;]+);/);
    const mimeType = mimeMatch ? mimeMatch[1] : 'image/png';
    
    // Create blob from bytes
    blob = new Blob([bytes], { type: mimeType });
  } catch (error) {
    console.error('Error converting data URL to blob:', error);
    throw new Error('Failed to process image. Please try again.');
  }

  // Create FormData with the image file
  const formData = new FormData();
  // Determine file extension from MIME type
  const extension = blob.type.includes('jpeg') ? '.jpg' : blob.type.includes('png') ? '.png' : '.png';
  formData.append('file', blob, `photo${extension}`);

  const uploadResponse = await fetch(`${API_BASE_URL}/blob-storage/upload/image/${candidateId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Don't set Content-Type header - browser will set it with boundary for FormData
    },
    body: formData,
  });

  if (!uploadResponse.ok) {
    const error = await uploadResponse.json().catch(() => ({ detail: 'Failed to upload image' }));
    throw new Error(error.detail || 'Failed to upload image');
  }

  return uploadResponse.json();
};

// ==================== Redis Integration Functions ====================

export interface StartTestRequest {
  duration_minutes?: number; // Optional, defaults to backend default
}

export interface StartTestResponse {
  success: boolean;
  message: string;
  test_start_time: string; // ISO timestamp
  remaining_seconds: number;
}

/**
 * Start a test session and load questions into Redis
 * This MUST be called before fetching questions to ensure Redis is populated
 */
export const startTest = async (
  candidateId?: string,
  token?: string,
  durationMinutes?: number
): Promise<StartTestResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  // Use provided token or get from localStorage
  const finalToken = token || getAuthToken();
  if (!finalToken) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/test/start`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${finalToken}`,
      },
      body: JSON.stringify({
        duration_minutes: durationMinutes,
      } as StartTestRequest),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to start test' }));
    throw new Error(error.detail || 'Failed to start test');
  }

  return response.json();
};

export interface HeartbeatRequest {
  client_timestamp?: string; // Optional ISO timestamp
}

export interface HeartbeatResponse {
  success: boolean;
  message: string;
  server_timestamp: string; // ISO timestamp
  remaining_seconds: number;
}

/**
 * Send heartbeat every 2 minutes to keep test session alive
 * Prevents auto-completion due to inactivity
 */
export const sendHeartbeat = async (
  candidateId?: string,
  token?: string,
  clientTimestamp?: Date
): Promise<HeartbeatResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  // Use provided token or get from localStorage
  const finalToken = token || getAuthToken();
  if (!finalToken) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/test/heartbeat`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${finalToken}`,
      },
      body: JSON.stringify({
        client_timestamp: clientTimestamp?.toISOString(),
      } as HeartbeatRequest),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to send heartbeat' }));
    throw new Error(error.detail || 'Failed to send heartbeat');
  }

  return response.json();
};

export interface CompleteTestRequest {
  completion_method?: 'manual' | 'tab_close' | 'timer_expired' | 'heartbeat_timeout' | 'auto';
  mcq_answers?: {
    answers: Array<{
      question_uuid: string;
      candidate_answer: string; // Option number as string: "1", "2", "3", or "4"
    }>;
  };
  coding_answers?: Record<string, unknown>; // Optional - not yet implemented
  system_design_data?: Record<string, unknown>; // Optional - not yet implemented
  sections_completed?: {
    mcq?: boolean;
    coding?: boolean;
    system_design?: boolean;
  };
  section_timings?: {
    mcq?: number; // duration in seconds
    coding?: number; // duration in seconds
    system_design?: number; // duration in seconds
  };
  integrity?: {
    multiple_face: 'yes' | 'no';
    full_screen_exits: number;
    tab_change: number;
  };
}

export interface CompleteTestResponse {
  success: boolean;
  message: string;
  completed_at: string | null; // ISO datetime string
}

/**
 * Complete a test session and save all answers
 * This is the final endpoint to mark test as completed
 */
export const completeTest = async (
  request: CompleteTestRequest,
  candidateId?: string
): Promise<CompleteTestResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  console.log('=== COMPLETE TEST REQUEST ===');
  console.log('Candidate ID (from localStorage):', finalCandidateId);
  console.log('Request:', JSON.stringify(request, null, 2));
  console.log('============================');

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/test/complete`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to complete test' }));
    throw new Error(error.detail || 'Failed to complete test');
  }

  const data = await response.json();
  console.log('=== COMPLETE TEST RESPONSE ===');
  console.log('Response:', JSON.stringify(data, null, 2));
  console.log('=============================');
  
  return data;
};

export interface TestStatusResponse {
  success: boolean;
  message: string;
  status: 'active' | 'completed' | null;
  remaining_seconds: number;
  sections_completed: {
    mcq?: boolean;
    coding?: boolean;
    system_design?: boolean;
  };
  last_activity: string | null; // ISO datetime string
}

/**
 * Get current test status including remaining time
 * Used to sync timer on page load/refresh
 */
export const getTestStatus = async (
  candidateId?: string
): Promise<TestStatusResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/test/status`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to get test status' }));
    throw new Error(error.detail || 'Failed to get test status');
  }

  return response.json();
};

export interface InterviewSummaryResponse {
  success: boolean;
  message: string;
  candidate: {
    candidate_id: string;
    candidate_reference_number?: string;
    name: string;
    email: string;
    role: string;
    status: string;
    scheduled_date?: string;
    test_completed_at?: string;
  };
  summary?: string;
  mcq_analysis?: Record<string, unknown>;
  coding_analysis?: Record<string, unknown>;
  system_design_analysis?: Record<string, unknown>;
  cheat_metrics?: Record<string, unknown>;
  section_timings?: {
    mcq?: number; // duration in seconds
    coding?: number; // duration in seconds
    system_design?: number; // duration in seconds
  };
}

/**
 * Get interview summary for a candidate
 */
export const getInterviewSummary = async (
  candidateId?: string
): Promise<InterviewSummaryResponse> => {
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required.');
  }

  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found. Please login again.');
  }

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/interview-summary`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to get interview summary' }));
    throw new Error(error.detail || 'Failed to get interview summary');
  }

  return response.json();
};

