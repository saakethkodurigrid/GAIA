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

  const data = await response.json();
  console.log('[createSession] System Design Question from Backend:', {
    session_id: data.session_id,
    question_text: data.question_text,
    question_uuid: data.question_uuid,
    full_response: data
  });
  return data;
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

  const data = await response.json();
  console.log('[getQuestionByUuid] System Design Question from Backend:', {
    uuid,
    question_id: data.question_id,
    question: data.question,
    evaluation_criteria: data.evaluation_criteria,
    tags: data.tags,
    full_response: data
  });
  return data;
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

// Proactive Prompts Types
export interface ProactivePromptResponse {
  has_prompt: boolean;
  prompt?: string | null;
}

// Check Proactive Prompts API
export const checkProactivePrompts = async (sessionId: string): Promise<ProactivePromptResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${sessionId}/check-prompts`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to check prompts' }));
    throw new Error(error.detail || 'Failed to check prompts');
  }

  return response.json();
};

// Chat History Types
export interface ChatHistoryResponse {
  messages: Array<{
    role: string;
    content: string;
    timestamp?: string | null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
  }>;
}

// Get Chat History API
export const getChatHistory = async (sessionId: string): Promise<ChatHistoryResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${sessionId}/chat-history`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch chat history' }));
    throw new Error(error.detail || 'Failed to fetch chat history');
  }

  return response.json();
};

// Final Report Types
export interface FinalReportResponse {
  session_id: string;
  question: string;
  average_scores: Record<string, number>;
  timeline: Array<{
    timestamp: string;
    event: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
  }>;
  total_versions: number;
  total_messages: number;
  lowest_area?: string | null;
  suggested_learning: string[];
}

// End Session API
export const endSession = async (sessionId: string): Promise<FinalReportResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${sessionId}/end`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to end session' }));
    throw new Error(error.detail || 'Failed to end session');
  }

  return response.json();
};

// Get Report API
export const getReport = async (sessionId: string): Promise<FinalReportResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${sessionId}/report`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch report' }));
    throw new Error(error.detail || 'Failed to fetch report');
  }

  return response.json();
};

// Assigned Question Types (from candidate API)
export interface AssignedQuestionResponse {
  candidate_id: string;
  question_uuid: string;
  question: string;
  evaluation_criteria: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  tags?: Record<string, any> | null;
  score?: number | null;
  diagram?: string | null;
  test_completed: boolean;
}

// Get Assigned Question API (from candidate endpoint)
export const getAssignedQuestion = async (candidateId: string): Promise<AssignedQuestionResponse> => {
  const response = await fetch(`${API_BASE_URL}/candidate/${candidateId}/assigned-question`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${getAuthToken() || ''}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch assigned question' }));
    console.error('[getAssignedQuestion] API Error:', {
      status: response.status,
      statusText: response.statusText,
      error: error
    });
    throw new Error(error.detail || 'Failed to fetch assigned question');
  }

  const data = await response.json();
  console.log('[getAssignedQuestion] API Response:', {
    candidateId,
    response: data
  });
  return data;
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

