import { API_BASE_URL } from '../utils/config';
import type { SystemDesignProblem } from '../types';

// Types matching backend schemas
export interface SessionCreateRequest {
  question_id?: string;
  question_text?: string;
  question_uuid?: string;
  tag?: string;
  candidate_id?: string;
}

export interface SessionResponse {
  session_id: string;
  question_text: string;
  question_uuid?: string | null;
}

export interface QuestionResponse {
  uuid: string;
  question_id: string;
  question: string;
  evaluation_criteria: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  tags?: Record<string, any> | null;
}

// Get auth token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
};

// API Functions
export const createSession = async (request?: Partial<SessionCreateRequest>): Promise<SessionResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
    body: JSON.stringify(request || {}),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create session' }));
    throw new Error(error.detail || 'Failed to create session');
  }

  return response.json();
};

export const getQuestionByUuid = async (uuid: string): Promise<QuestionResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/questions/${uuid}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch question' }));
    throw new Error(error.detail || 'Failed to fetch question');
  }

  return response.json();
};

// Canvas Update Types
export interface CanvasData {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  elements: any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  appState?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  files?: any;
}

export interface CanvasUpdateRequest {
  session_id: string;
  canvas_data: CanvasData;
  action: 'save' | 'submit' | 'update';
  change_hash?: string;
}

export interface CanvasUpdateResponse {
  status: string;
  version?: number;
  evaluation?: {
    scores: Record<string, number>;
    feedback: string;
    follow_up?: string;
  };
  evaluation_message?: string;
}

// Canvas Update API
export const updateCanvas = async (request: CanvasUpdateRequest): Promise<CanvasUpdateResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/canvas/update`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update canvas' }));
    throw new Error(error.detail || 'Failed to update canvas');
  }

  return response.json();
};

// Chat Message Types
export interface ChatMessageRequest {
  message: string;
  session_id: string;
  canvas_data?: CanvasData;
}

export interface ChatMessageResponse {
  user_message: {
    role: string;
    content: string;
    timestamp?: string | null;
  };
  ai_response?: string | null;
  evaluation?: {
    scores: Record<string, number>;
    feedback: string;
    follow_up?: string | null;
  };
}

// Chat Message API
export const sendChatMessage = async (request: ChatMessageRequest): Promise<ChatMessageResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to send message' }));
    throw new Error(error.detail || 'Failed to send message');
  }

  return response.json();
};

// Legacy function for backward compatibility
export const MOCK_SYSTEM_DESIGN_PROBLEM: SystemDesignProblem = {
  id: 1,
  title: 'Design a URL Shortener',
  description: 'Design a service like TinyURL or bit.ly that takes a long URL and returns a shortened URL. The service should handle millions of requests per day and provide analytics on URL usage.',
  requirements: [
    'Generate a short, unique URL for a given long URL',
    'Handle 100 million URLs per day',
    'Support URL expiration (optional)',
    'Provide click analytics',
    'Ensure high availability and scalability'
  ]
};

export const fetchSystemDesignProblem = async (): Promise<SystemDesignProblem> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_SYSTEM_DESIGN_PROBLEM);
    }, 500);
  });
};

// Legacy function - kept for backward compatibility
export const submitSystemDesign = async (
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _problemId: number,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
  _excalidrawData: any,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _notes: string
): Promise<{ success: boolean; message: string }> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ success: true, message: 'System design submitted successfully' });
    }, 1000);
  });
};

// Legacy function - kept for backward compatibility
export const askClarifyingQuestion = async (
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _question: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _problemId: number
): Promise<string> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Mock AI response
      const responses = [
        'That\'s a great question! Let me clarify: The system should handle high availability and be able to scale horizontally.',
        'Based on the requirements, you should consider the following: database sharding, caching layer, and load balancing.',
        'Good point! You might want to think about the trade-offs between consistency and availability in your design.',
        'Consider the CAP theorem here - you may need to choose between consistency and availability depending on your use case.'
      ];
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      resolve(randomResponse);
    }, 1000);
  });
};

