import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { 
  createSession, 
  sendChatMessage, 
  updateCanvas,
  getAssignedQuestion,
  getChatHistory,
  createProactivePromptsStream,
  endSession
} from '../api/systemDesign.api';
import type { SystemDesignContextType, SystemDesignProblem, ChatMessage } from '../types';
import { getTestStatus } from '../api/candidate.api';
import { localStorage as storage } from '../utils/localStorage';

const TIMER_DURATION = 180 * 60; // 180 minutes (3 hours)

const SystemDesignContext = createContext<SystemDesignContextType | undefined>(undefined);

interface SystemDesignProviderProps {
  children: ReactNode;
}

export const SystemDesignProvider = ({ children }: SystemDesignProviderProps) => {
  const { user } = useAuth();
  const [problem, setProblem] = useState<SystemDesignProblem | null>(null);
  const [excalidrawData, setExcalidrawData] = useState<any>(null);
  const [notes, setNotes] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  const getInitialTime = (): number => {
    const stored = storage.getRemainingTime();
    if (stored !== null && stored > 0) {
      return stored;
    }
    return TIMER_DURATION;
  };

  const [timeRemaining, setTimeRemaining] = useState(getInitialTime());
  const [isLoading, setIsLoading] = useState(true);
  const [questionUuid, setQuestionUuid] = useState<string | null>(null);
  const [isTimerInitialized, setIsTimerInitialized] = useState(false);
  const sessionCreatedRef = useRef(false);
  const proactivePromptIntervalRef = useRef<number | null>(null);
  const sseAbortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Sync timer from backend on mount and update localStorage
  useEffect(() => {
    const syncTimer = async () => {
      const candidateId = user?.candidateId;
      if (!candidateId) return;

      try {
        const status = await getTestStatus(candidateId);
        if (status.success && status.status === 'active' && status.remaining_seconds >= 0) {
          setTimeRemaining(status.remaining_seconds);
          storage.setTimerEndTime(status.remaining_seconds);
          setIsTimerInitialized(true);
        } else {
          const localTime = storage.getRemainingTime();
          if (localTime !== null && localTime > 0) {
            setTimeRemaining(localTime);
          }
          setIsTimerInitialized(true);
        }
      } catch (error) {
        console.error('Failed to sync timer from backend:', error);
        const localTime = storage.getRemainingTime();
        if (localTime !== null && localTime > 0) {
          setTimeRemaining(localTime);
        }
        setIsTimerInitialized(true);
      }
    };

    const localTime = storage.getRemainingTime();
    if (localTime !== null && localTime > 0) {
      setTimeRemaining(localTime);
      setIsTimerInitialized(true);
    }

    syncTimer();
    const syncInterval = setInterval(syncTimer, 30000);
    return () => clearInterval(syncInterval);
  }, [user?.candidateId]);

  // Create session and load question on mount
  useEffect(() => {
    const initializeSession = async () => {
      if (sessionCreatedRef.current) return;

      if (!user?.candidateId) {
        console.log('Waiting for user authentication...');
        return;
      }

      sessionCreatedRef.current = true;
      setIsLoading(true);

      try {
        let assignedQuestion: any = null;
        try {
          console.log('Fetching assigned question...');
          assignedQuestion = await getAssignedQuestion(user.candidateId);
          console.log('Assigned question fetched:', assignedQuestion);
        } catch (error: any) {
          console.log('No assigned question found or test not in progress:', error.message);
        }

        console.log('Creating session...');
        const sessionResponse = await createSession({
          question_uuid: assignedQuestion?.question_uuid || undefined,
        });

        console.log('Session created:', sessionResponse);

        if (sessionResponse.question_uuid) {
          setQuestionUuid(sessionResponse.question_uuid);
        } else if (assignedQuestion?.question_uuid) {
          setQuestionUuid(assignedQuestion.question_uuid);
        } else {
          throw new Error('No question_uuid available from session or assigned question');
        }

        let problemData: SystemDesignProblem;

        if (assignedQuestion) {
          const criteria =
            (assignedQuestion as any).evaluation_criteria as string | undefined;

          problemData = {
            id: 1,
            title: 'System Design Problem',
            description: assignedQuestion.question,
            requirements: criteria
              ? criteria.split('\n').filter((line: string) => line.trim())
              : [],
          };
        } else if (sessionResponse.question_text) {
          console.log('Using question_text from session');
          problemData = {
            id: 1,
            title: 'System Design Problem',
            description: sessionResponse.question_text,
            requirements: [],
          };
        } else {
          console.warn('No question_text in session response, using fallback');
          problemData = {
            id: 1,
            title: 'System Design Problem',
            description: 'An error occurred loading the problem. Please refresh the page.',
            requirements: [],
          };
        }

        setProblem(problemData);
        console.log('Question loaded:', problemData);

        if (sessionResponse.current_canvas) {
          console.log('Loading canvas data from session:', sessionResponse.current_canvas);
          setExcalidrawData(sessionResponse.current_canvas);
        }

        const uuidToUse = sessionResponse.question_uuid || assignedQuestion?.question_uuid;
        if (uuidToUse) {
          try {
            const chatHistory = await getChatHistory(uuidToUse);
            if (chatHistory.messages && chatHistory.messages.length > 0) {
              const mappedMessages: ChatMessage[] = chatHistory.messages.map((msg, index) => ({
                id: `${msg.timestamp || index}`,
                role: msg.role as 'user' | 'assistant',
                content: msg.content,
                timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
              }));
              setChatMessages(mappedMessages);
              console.log('Chat history loaded:', mappedMessages.length, 'messages');
            }
          } catch (error) {
            console.error('Error loading chat history:', error);
          }
        }

        setIsLoading(false);
      } catch (error) {
        console.error('Error initializing session:', error);
        try {
          const mockData = await import('../api/systemDesign.api').then(m => m.MOCK_SYSTEM_DESIGN_PROBLEM);
          setProblem(mockData);
        } catch {
          setProblem({
            id: 1,
            title: 'System Design Problem',
            description: 'An error occurred loading the problem. Please refresh the page.',
            requirements: [],
          });
        }
        setIsLoading(false);
      }
    };

    initializeSession();
  }, [user?.candidateId]);

  // SSE connection for proactive prompts
  useEffect(() => {
    if (!questionUuid) return;

    const cleanup = () => {
      if (sseAbortControllerRef.current) {
        sseAbortControllerRef.current.abort();
        sseAbortControllerRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    const handleSSEMessage = (event: { has_prompt: boolean; prompt?: string | null; closed?: boolean; error?: string }) => {
      console.log('[SSE] Received event:', event);

      if (event.has_prompt && event.prompt) {
        console.log('[SSE] ✅ Proactive prompt received:', event.prompt);

        const proactiveMessage: ChatMessage = {
          id: `proactive-${Date.now()}`,
          role: 'assistant',
          content: event.prompt,
          timestamp: new Date(),
        };

        setChatMessages((prev) => {
          const exists = prev.some(
            (msg) => msg.role === 'assistant' && msg.content === event.prompt
          );
          if (!exists) {
            console.log('[SSE] ✅ Adding prompt to chat messages. Total messages:', prev.length + 1);
            return [...prev, proactiveMessage];
          } else {
            console.log('[SSE] ⚠️ Prompt already exists, skipping duplicate');
            return prev;
          }
        });
      } else if (event.has_prompt === false) {
        console.log('[SSE] Heartbeat: No prompt available');
      }

      if (event.closed) {
        console.log('SSE stream closed by server (no activity)');
        cleanup();
      }

      if (event.error) {
        console.error('SSE stream error:', event.error);
      }
    };

    const handleSSEError = (error: Error) => {
      console.error('SSE connection error:', error);
      cleanup();

      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (questionUuid) {
          console.log('Attempting to reconnect SSE stream...');
          try {
            sseAbortControllerRef.current = createProactivePromptsStream(
              questionUuid,
              handleSSEMessage,
              handleSSEError,
              () => {
                console.log('SSE stream closed');
                cleanup();
              }
            );
          } catch (err) {
            console.error('Failed to reconnect SSE stream:', err);
            reconnectTimeoutRef.current = window.setTimeout(() => {
              if (questionUuid) {
                try {
                  sseAbortControllerRef.current = createProactivePromptsStream(
                    questionUuid,
                    handleSSEMessage,
                    handleSSEError,
                    () => {
                      console.log('SSE stream closed');
                      cleanup();
                    }
                  );
                } catch (reconnectErr) {
                  console.error('Failed to reconnect SSE stream after retry:', reconnectErr);
                }
              }
            }, 3000);
          }
        }
      }, 3000);
    };

    const handleSSEClose = () => {
      console.log('SSE stream closed');
      cleanup();
    };

    try {
      console.log('[SSE] 🔌 Setting up SSE connection for proactive prompts...');
      console.log('[SSE] 🔌 Question UUID:', questionUuid);
      sseAbortControllerRef.current = createProactivePromptsStream(
        questionUuid,
        handleSSEMessage,
        handleSSEError,
        handleSSEClose
      );
      console.log('[SSE] ✅ SSE connection established successfully');
    } catch (error) {
      console.error('[SSE] ❌ Failed to create SSE stream:', error);
    }

    return () => {
      cleanup();
      if (proactivePromptIntervalRef.current) {
        clearInterval(proactivePromptIntervalRef.current);
        proactivePromptIntervalRef.current = null;
      }
    };
  }, [questionUuid]);

  // Timer countdown (only start after initial sync)
  useEffect(() => {
    if (!isTimerInitialized || timeRemaining <= 0) {
      if (timeRemaining <= 0) {
        storage.clearTimer();
      }
      return;
    }

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        const newTime = prev <= 1 ? 0 : prev - 1;
        if (newTime > 0) {
          storage.setTimerEndTime(newTime);
        } else {
          storage.clearTimer();
        }
        return newTime;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isTimerInitialized, timeRemaining]);

  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const handleUpdateExcalidrawData = useCallback((data: any) => {
    setExcalidrawData(data);
  }, []);

  // Auto-update canvas to backend (debounced)
  useEffect(() => {
    if (!questionUuid || !excalidrawData) return;

    const canvasUpdateTimeout = setTimeout(async () => {
      try {
        await updateCanvas({
          question_uuid: questionUuid,
          canvas_data: {
            elements: excalidrawData.elements || [],
            appState: excalidrawData.appState,
            files: excalidrawData.files,
          },
          action: 'update', // Lightweight sync
        }, user.candidateId);
        console.log('Canvas updated to backend');
      } catch (error) {
        console.error('Failed to update canvas:', error);
      }
    }, 2000);

    return () => {
      clearTimeout(canvasUpdateTimeout);
    };
  }, [excalidrawData, questionUuid]);

  const handleUpdateNotes = useCallback((newNotes: string) => {
    setNotes(newNotes);
  }, []);

  const handleSendMessage = useCallback(async (message: string) => {
    if (!message.trim() || !questionUuid) {
      console.error('Cannot send message: missing question UUID');
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date()
    };

    setChatMessages((prev) => [...prev, userMessage]);

    try {
      const canvasData = excalidrawData ? {
        elements: excalidrawData.elements || [],
        appState: excalidrawData.appState,
        files: excalidrawData.files,
      } : undefined;

      const response = await sendChatMessage({
        message: message.trim(),
        question_uuid: questionUuid,
        canvas_data: canvasData,
      });

      if (response.ai_response) {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.ai_response,
          timestamp: new Date()
        };
        setChatMessages((prev) => [...prev, assistantMessage]);
      }

      if (response.evaluation) {
        console.log('Evaluation received:', response.evaluation);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setChatMessages((prev) => [...prev, errorMessage]);
    }
  }, [questionUuid, excalidrawData]);

  const handleClearCanvas = useCallback((excalidrawAPI: any) => {
    if (excalidrawAPI) {
      try {
        const appState = excalidrawAPI.getAppState();
        excalidrawAPI.updateScene({
          elements: [],
          appState: appState ? {
            ...appState,
            scrollX: 0,
            scrollY: 0,
            zoom: { value: 1 }
          } : undefined
        });
      } catch (error) {
        console.error('Error clearing diagram:', error);
      }
    }
    setExcalidrawData(null);
  }, []);

  const handleSubmitSolution = useCallback(async () => {
    if (!questionUuid || !excalidrawData) {
      console.error('Cannot submit: missing question UUID or canvas data');
      return;
    }

    try {
      await updateCanvas({
        question_uuid: questionUuid,
        canvas_data: {
          elements: excalidrawData.elements || [],
          appState: excalidrawData.appState,
          files: excalidrawData.files,
        },
        action: 'submit',
      }, user.candidateId);
      console.log('Solution submitted successfully');

      try {
        const report = await endSession(questionUuid, user.candidateId);
        console.log('Final report received:', report);
      } catch (error) {
        console.error('Error ending session:', error);
      }
    } catch (error) {
      console.error('Error submitting solution:', error);
      throw error;
    }
  }, [questionUuid, excalidrawData]);

  const value: SystemDesignContextType = {
    problem,
    excalidrawData,
    notes,
    chatMessages,
    timeRemaining,
    isLoading,
    updateExcalidrawData: handleUpdateExcalidrawData,
    updateNotes: handleUpdateNotes,
    sendMessage: handleSendMessage,
    clearCanvas: handleClearCanvas,
    formatTime,
    submitSolution: handleSubmitSolution
  };

  return <SystemDesignContext.Provider value={value}>{children}</SystemDesignContext.Provider>;
};

export const useSystemDesign = (): SystemDesignContextType => {
  const context = useContext(SystemDesignContext);
  if (!context) {
    throw new Error('useSystemDesign must be used within SystemDesignProvider');
  }
  return context;
};
