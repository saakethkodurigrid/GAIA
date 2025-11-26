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
 * Schedule a test for the authenticated candidate
 */
export const scheduleTest = async (
  scheduledDate: Date,
  token: string
): Promise<ScheduleTestResponse> => {
  // Convert date to ISO string
  const scheduledDateISO = scheduledDate.toISOString();
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

