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
  question_text: string;
  question_uuid?: string | null;
  current_canvas?: CanvasData | null;
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
    question_text: data.question_text,
    question_uuid: data.question_uuid,
    full_response: data
  });
  return data;
};

// Removed getQuestionByUuid - endpoint does not exist in backend
// Use question_text from createSession response instead

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
  question_uuid: string;
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
  question_uuid: string;
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

export interface SSEPromptEvent {
  has_prompt: boolean;
  prompt?: string | null;
  closed?: boolean;
  error?: string;
}

// Removed checkProactivePrompts - endpoint does not exist in backend
// Use createProactivePromptsStream for SSE streaming instead

// SSE Stream for Proactive Prompts
// Returns an AbortController to allow cleanup
export const createProactivePromptsStream = (
  questionUuid: string,
  onMessage: (event: SSEPromptEvent) => void,
  onError?: (error: Error) => void,
  onClose?: () => void
): AbortController => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('No authentication token available');
  }

  const abortController = new AbortController();

  const url = `${API_BASE_URL}/system-design/sessions/${questionUuid}/prompts-stream`;

  // Use fetch with ReadableStream to support custom headers (EventSource doesn't support headers)
  fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'text/event-stream',
    },
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body reader available');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onClose?.();
          break;
        }

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages (separated by \n\n)
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || ''; // Keep incomplete message in buffer

        for (const message of messages) {
          if (message.trim() === '') continue;

          // Parse SSE format: "data: {...}" (handle multi-line data fields)
          const lines = message.split('\n');
          let dataContent = '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              // If we already have content, append with newline (multi-line data)
              if (dataContent) {
                dataContent += '\n' + line.substring(6);
              } else {
                dataContent = line.substring(6);
              }
            } else if (line.startsWith(':')) {
              // Comment line, ignore
              continue;
            } else if (line.trim() === '') {
              // Empty line, ignore
              continue;
            }
          }

          if (dataContent) {
            try {
              const data: SSEPromptEvent = JSON.parse(dataContent);
              onMessage(data);

              // Handle stream closure
              if (data.closed) {
                abortController.abort();
                onClose?.();
                return;
              }

              // Handle errors from stream
              if (data.error) {
                onError?.(new Error(data.error));
              }
            } catch (error) {
              console.error('Error parsing SSE message:', error, 'Content:', dataContent);
              onError?.(error as Error);
            }
          }
        }
      }
    })
    .catch((error) => {
      if (error.name === 'AbortError') {
        // Clean abort, don't treat as error
        return;
      }
      console.error('SSE connection error:', error);
      onError?.(error);
    });

  return abortController;
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
export const getChatHistory = async (questionUuid: string): Promise<ChatHistoryResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${questionUuid}/chat-history`, {
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
  question_uuid: string;
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
export const endSession = async (questionUuid: string): Promise<FinalReportResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${questionUuid}/end`, {
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
export const getReport = async (questionUuid: string): Promise<FinalReportResponse> => {
  const response = await fetch(`${API_BASE_URL}/system-design/sessions/${questionUuid}/report`, {
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

