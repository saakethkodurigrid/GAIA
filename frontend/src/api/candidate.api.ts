import { API_BASE_URL } from '../utils/config';

export interface ScheduleTestRequest {
  scheduled_date: string; // ISO format datetime string
}

export interface ScheduleTestResponse {
  success: boolean;
  message: string;
  scheduled_date: string | null; // ISO format datetime string
}

/**
 * Convert a Date object to IST (Indian Standard Time) format
 * Treats the date/time as IST time and formats it with +05:30 offset
 * IST is UTC+5:30
 */
const toISTString = (date: Date): string => {
  // Extract date components (treating them as IST time)
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  // Format as ISO string with IST offset (+05:30)
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}+05:30`;
};

/**
 * Schedule a test for the authenticated candidate
 */
export const scheduleTest = async (
  scheduledDate: Date,
  token: string
): Promise<ScheduleTestResponse> => {
  // Convert date to IST format string
  const scheduledDateISO = toISTString(scheduledDate);
  
  // Log what's being sent to backend
  console.log('=== API Call: scheduleTest ===');
  console.log('Input Date object:', scheduledDate);
  console.log('Input Date ISO:', scheduledDate.toISOString());
  console.log('Input Date Local:', scheduledDate.toString());
  console.log('Converted IST string:', scheduledDateISO);
  console.log('Request body:', JSON.stringify({
    scheduled_date: scheduledDateISO,
  }));
  console.log('API Endpoint:', `${API_BASE_URL}/candidate/schedule-test`);
  console.log('================================');
  
  // const candidateId = localStorage.getItem('candidate_id') || '';
  // if (!candidateId) {
  //   throw new Error('Candidate ID not found. Please login again.');
  // }
  const response = await fetch(`${API_BASE_URL}/candidate/schedule-test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    
    body: JSON.stringify({
      scheduled_date: scheduledDateISO,
      // candidate_id: candidateId,
    } as ScheduleTestRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to schedule test' }));
    throw new Error(error.detail || 'Failed to schedule test');
  }

  return response.json();
};

// Get auth token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
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

  // Convert base64 data URL to blob
  const response = await fetch(imageDataUrl);
  const blob = await response.blob();

  // Create FormData with the image file
  const formData = new FormData();
  formData.append('file', blob, 'photo.png');

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
  candidateId: string,
  token: string,
  durationMinutes?: number
): Promise<StartTestResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/candidate/${candidateId}/test/start`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
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
  candidateId: string,
  token: string,
  clientTimestamp?: Date
): Promise<HeartbeatResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/candidate/${candidateId}/test/heartbeat`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
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

