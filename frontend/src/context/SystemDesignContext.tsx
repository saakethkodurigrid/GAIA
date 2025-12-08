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

const TIMER_DURATION = 60 * 60; // 60 minutes

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
  const [timeRemaining, setTimeRemaining] = useState(TIMER_DURATION);
  const [isLoading, setIsLoading] = useState(true);
  const [questionUuid, setQuestionUuid] = useState<string | null>(null);
  const sessionCreatedRef = useRef(false);
  const proactivePromptIntervalRef = useRef<number | null>(null);
  const sseAbortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Create session and load question on mount
  useEffect(() => {
    const initializeSession = async () => {
      // Prevent multiple session creations
      if (sessionCreatedRef.current) return;
      
      // Wait for user data to be available
      if (!user?.candidateId) {
        console.log('Waiting for user authentication...');
        return;
      }

      sessionCreatedRef.current = true;
      setIsLoading(true);

      try {
        // Step 1: Fetch assigned question (if test is in progress)
        let assignedQuestion = null;
        try {
          console.log('Fetching assigned question...');
          assignedQuestion = await getAssignedQuestion(user.candidateId);
          console.log('Assigned question fetched:', assignedQuestion);
        } catch (error: any) {
          // If test is not in progress, this will fail - that's okay, we'll create session without it
          console.log('No assigned question found or test not in progress:', error.message);
        }

        // Step 2: Create session with assigned question UUID (if available)
        // Note: candidate_id is auto-filled by backend from authenticated user, don't send it
        console.log('Creating session...');
        const sessionResponse = await createSession({
          question_uuid: assignedQuestion?.question_uuid || undefined,
        });

        console.log('Session created:', sessionResponse);
        
        // Store question_uuid (required for all subsequent API calls)
        if (sessionResponse.question_uuid) {
          setQuestionUuid(sessionResponse.question_uuid);
        } else {
          // If no question_uuid, try to use assigned question UUID
          if (assignedQuestion?.question_uuid) {
            setQuestionUuid(assignedQuestion.question_uuid);
          } else {
            throw new Error('No question_uuid available from session or assigned question');
          }
        }

        // Step 3: Load question details
        // Priority: Use question_text from session response (always available)
        // Only fetch by UUID if we need additional details (evaluation_criteria, etc.)
        let problemData: SystemDesignProblem;
        
        if (assignedQuestion) {
          // Use assigned question data (has evaluation_criteria)
          problemData = {
            id: 1,
            title: 'System Design Problem',
            description: assignedQuestion.question,
            requirements: assignedQuestion.evaluation_criteria
              ? assignedQuestion.evaluation_criteria.split('\n').filter(line => line.trim())
              : [],
          };
        } else if (sessionResponse.question_text) {
          // Use question_text from session (always available)
          console.log('Using question_text from session');
          problemData = {
            id: 1,
            title: 'System Design Problem',
            description: sessionResponse.question_text,
            requirements: [],
          };
        } else {
          // Last resort: Use hardcoded fallback
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

        // Step 4: Load canvas data if available
        if (sessionResponse.current_canvas) {
          console.log('Loading canvas data from session:', sessionResponse.current_canvas);
          setExcalidrawData(sessionResponse.current_canvas);
        }

        // Step 5: Load chat history if question_uuid exists
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
            // Continue without chat history
          }
        }

        setIsLoading(false);
      } catch (error) {
        console.error('Error initializing session:', error);
        // Fallback to mock data on error
        try {
          const mockData = await import('../api/systemDesign.api').then(m => m.MOCK_SYSTEM_DESIGN_PROBLEM);
          setProblem(mockData);
        } catch {
          // If even mock fails, set a basic problem
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

    // Cleanup function
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

    // Function to handle SSE messages
    const handleSSEMessage = (event: { has_prompt: boolean; prompt?: string | null; closed?: boolean; error?: string }) => {
      // Debug: Log all SSE events
      console.log('[SSE] Received event:', event);
      
      if (event.has_prompt && event.prompt) {
        console.log('[SSE] ✅ Proactive prompt received:', event.prompt);
        
        // Add proactive prompt as assistant message
        const proactiveMessage: ChatMessage = {
          id: `proactive-${Date.now()}`,
          role: 'assistant',
          content: event.prompt,
          timestamp: new Date(),
        };
        
        // Check if this prompt was already shown
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
        // Heartbeat - no prompt available
        console.log('[SSE] Heartbeat: No prompt available');
      }

      // Handle stream closure
      if (event.closed) {
        console.log('SSE stream closed by server (no activity)');
        cleanup();
      }

      // Handle errors from stream
      if (event.error) {
        console.error('SSE stream error:', event.error);
      }
    };

    // Function to handle SSE errors
    const handleSSEError = (error: Error) => {
      console.error('SSE connection error:', error);
      
      // Cleanup current connection
      cleanup();

      // Attempt to reconnect after 3 seconds
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
            // Try again after another 3 seconds
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

    // Function to handle SSE close
    const handleSSEClose = () => {
      console.log('SSE stream closed');
      cleanup();
    };

    // Create SSE connection
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
      // SSE is the only method available - no fallback polling endpoint exists
      // The stream will automatically reconnect if the connection is lost
    }

    return () => {
      cleanup();
      if (proactivePromptIntervalRef.current) {
        clearInterval(proactivePromptIntervalRef.current);
        proactivePromptIntervalRef.current = null;
      }
    };
  }, [questionUuid]);

  // Timer countdown
  useEffect(() => {
    if (timeRemaining <= 0) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeRemaining]);

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

    // Clear existing timeout
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
        });
        console.log('Canvas updated to backend');
      } catch (error) {
        console.error('Failed to update canvas:', error);
      }
    }, 2000); // Update backend 2 seconds after user stops drawing

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

    // Create user message for immediate display
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date()
    };

    setChatMessages((prev) => [...prev, userMessage]);

    try {
      // Prepare canvas data if available
      const canvasData = excalidrawData ? {
        elements: excalidrawData.elements || [],
        appState: excalidrawData.appState,
        files: excalidrawData.files,
      } : undefined;

      // Send message to backend with canvas data
      const response = await sendChatMessage({
        message: message.trim(),
        question_uuid: questionUuid,
        canvas_data: canvasData,
      });

      // Add AI response if available
      if (response.ai_response) {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.ai_response,
          timestamp: new Date()
        };
        setChatMessages((prev) => [...prev, assistantMessage]);
      }

      // Note: Evaluation data is included in the response but not displayed in chat
      // It could be used for showing evaluation scores in a separate UI component
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
      // First submit the canvas
      await updateCanvas({
        question_uuid: questionUuid,
        canvas_data: {
          elements: excalidrawData.elements || [],
          appState: excalidrawData.appState,
          files: excalidrawData.files,
        },
        action: 'submit',
      });
      console.log('Solution submitted successfully');

      // Then end the session to get final report
      try {
        const report = await endSession(questionUuid);
        console.log('Final report received:', report);
        // You can store the report or show it to the user
      } catch (error) {
        console.error('Error ending session:', error);
        // Continue even if ending session fails
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

