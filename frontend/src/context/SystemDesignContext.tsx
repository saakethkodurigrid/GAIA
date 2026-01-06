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
  // Initialize timer from localStorage or default
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

      // CRITICAL: Only allow timer sync if timer_started flag is set (i.e., user clicked "Start Assessment")
      const timerStarted = localStorage.getItem('timer_started') === 'true';
      if (!timerStarted) {
        console.log('[SystemDesignContext] Timer not started yet - skipping timer sync. User must click "Start Assessment" first.');
        return; // Don't sync timer if flag is not set
      }

      try {
        const status = await getTestStatus(candidateId);
        if (status.success && status.status === 'active' && status.remaining_seconds >= 0) {
          setTimeRemaining(status.remaining_seconds);
          // Update localStorage with backend time
          storage.setTimerEndTime(status.remaining_seconds);
          setIsTimerInitialized(true);
        } else {
          // If backend doesn't have active timer, check localStorage
          const localTime = storage.getRemainingTime();
          if (localTime !== null && localTime > 0) {
            setTimeRemaining(localTime);
          }
          setIsTimerInitialized(true);
        }
      } catch (error) {
        console.error('Failed to sync timer from backend:', error);
        // Fallback to localStorage if backend sync fails
        const localTime = storage.getRemainingTime();
        if (localTime !== null && localTime > 0) {
          setTimeRemaining(localTime);
        }
        setIsTimerInitialized(true);
      }
    };

    // CRITICAL: Only allow timer operations if timer_started flag is set
    const timerStarted = localStorage.getItem('timer_started') === 'true';
    if (!timerStarted) {
      console.log('[SystemDesignContext] Timer not started yet - skipping localStorage timer check. User must click "Start Assessment" first.');
      return; // Don't initialize timer if flag is not set
    }

    // First, try to use localStorage immediately for faster UI
    const localTime = storage.getRemainingTime();
    if (localTime !== null && localTime > 0) {
      setTimeRemaining(localTime);
      setIsTimerInitialized(true);
    }

    // Then sync with backend
    syncTimer();

    // Sync every 30 seconds to account for any drift
    const syncInterval = setInterval(syncTimer, 30000);

    return () => clearInterval(syncInterval);
  }, [user?.candidateId]);

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
        // Check cache first for instant loading
        const cachedSession = sessionStorage.getItem(`system_design_session_${user.candidateId}`);
        let sessionResponse: any;
        let assignedQuestion = null;
        
        if (cachedSession) {
          console.log('[SYSTEM DESIGN] Loading from cache for instant rendering...');
          sessionResponse = JSON.parse(cachedSession);
          setIsLoading(false);
          console.log('[SYSTEM DESIGN] ✅ Loaded instantly from cache');
        } else {
          // Cache miss - create session
          console.log('[SYSTEM DESIGN] Cache miss - creating session...');
          
          // Step 1: Fetch assigned question (if test is in progress)
          try {
            console.log('Fetching assigned question...');
            assignedQuestion = await getAssignedQuestion(user.candidateId);
            console.log('Assigned question fetched:', assignedQuestion);
          } catch (error: any) {
            // If test is not in progress, this will fail - that's okay, we'll create session without it
            console.log('No assigned question found or test not in progress:', error.message);
          }

          // Step 2: Create session with assigned question UUID (if available)
          console.log('Creating session...');
          sessionResponse = await createSession({
            question_uuid: assignedQuestion?.question_uuid || undefined,
          }, user.candidateId);
          
          // Cache for future use
          sessionStorage.setItem(`system_design_session_${user.candidateId}`, JSON.stringify(sessionResponse));
          setIsLoading(false);
        }

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
          // Use assigned question data
          problemData = {
            id: 1,
            title: 'System Design Problem',
            description: assignedQuestion.question,
            requirements: [],
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
            const chatHistory = await getChatHistory(uuidToUse, user.candidateId);
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
              },
              user?.candidateId
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
                    },
                    user?.candidateId
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
        handleSSEClose,
        user?.candidateId
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
        // Update localStorage with new remaining time
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

  // Recovery on reconnection - immediately sync data when connection is restored
  useEffect(() => {
    const handleOnline = async () => {
      console.log('🟢 [SystemDesign Recovery] Connection restored - initiating recovery...');
      
      const candidateId = user?.candidateId;
      if (!candidateId || isLoading) {
        console.log('⚠️ [SystemDesign Recovery] Skipping recovery - no candidate ID or still loading');
        return;
      }

      try {
        const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
        if (!token) {
          console.log('⚠️ [SystemDesign Recovery] No auth token found');
          return;
        }

        // 1. Send heartbeat immediately to reset timeout and get server time
        console.log('[SystemDesign Recovery] Step 1: Sending heartbeat...');
        const heartbeatResponse = await sendHeartbeat(candidateId, token);
        console.log('✅ [SystemDesign Recovery] Heartbeat sent successfully');

        // 2. Sync timer with server if there's a significant difference
        if (heartbeatResponse.remaining_seconds !== undefined) {
          const serverTime = heartbeatResponse.remaining_seconds;
          const localTime = timeRemaining;
          const timeDiff = Math.abs(serverTime - localTime);

          console.log(`[SystemDesign Recovery] Timer comparison - Local: ${localTime}s, Server: ${serverTime}s, Diff: ${timeDiff}s`);

          // If times differ by more than 5 seconds, sync with server
          if (timeDiff > 5) {
            console.log(`⚠️ [SystemDesign Recovery] Timer desync detected (${timeDiff}s difference), syncing with server...`);
            setTimeRemaining(serverTime);
            storage.setTimerEndTime(serverTime);
            console.log(`✅ [SystemDesign Recovery] Timer synced to ${serverTime}s`);
          } else {
            console.log('✅ [SystemDesign Recovery] Timer is in sync (difference < 5s)');
          }
        }

        // 3. Auto-save canvas data and chat messages
        console.log('[SystemDesign Recovery] Step 2: Syncing canvas and chat data...');
        if (questionUuid && excalidrawData) {
          try {
            // Save canvas data
            await updateCanvas({
              question_uuid: questionUuid,
              canvas_data: {
                elements: excalidrawData.elements || [],
                appState: excalidrawData.appState || {},
              }
            }, candidateId);
            console.log('✅ [SystemDesign Recovery] Canvas data saved');
          } catch (error) {
            console.error('⚠️ [SystemDesign Recovery] Failed to save canvas:', error);
          }

          try {
            // Save chat messages if any
            if (chatMessages.length > 0) {
              await saveChatMessage({
                question_uuid: questionUuid,
                messages: chatMessages
              }, candidateId);
              console.log('✅ [SystemDesign Recovery] Chat messages saved');
            }
          } catch (error) {
            console.error('⚠️ [SystemDesign Recovery] Failed to save chat:', error);
          }
        } else {
          console.log('⚠️ [SystemDesign Recovery] No canvas data to save');
        }

        console.log('✅ [SystemDesign Recovery] Full recovery completed successfully!');
      } catch (error) {
        console.error('❌ [SystemDesign Recovery] Recovery failed:', error);
        // Recovery failure shouldn't break the test - user can continue working
      }
    };

    // Listen for online event
    window.addEventListener('online', handleOnline);

    // Cleanup
    return () => {
      window.removeEventListener('online', handleOnline);
    };
  }, [user?.candidateId, timeRemaining, questionUuid, excalidrawData, chatMessages, isLoading]);

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
    if (!questionUuid || !excalidrawData || !user?.candidateId) return;

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
        }, user.candidateId);
        console.log('Canvas updated to backend');
      } catch (error) {
        console.error('Failed to update canvas:', error);
      }
    }, 2000); // Update backend 2 seconds after user stops drawing

    return () => {
      clearTimeout(canvasUpdateTimeout);
    };
  }, [excalidrawData, questionUuid, user?.candidateId]);

  const handleUpdateNotes = useCallback((newNotes: string) => {
    setNotes(newNotes);
  }, []);

  const handleSendMessage = useCallback(async (message: string) => {
    if (!message.trim() || !questionUuid || !user?.candidateId) {
      console.error('Cannot send message: missing question UUID or candidate ID');
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
      }, user.candidateId);

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
  }, [questionUuid, excalidrawData, user?.candidateId]);

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
    if (!questionUuid || !excalidrawData || !user?.candidateId) {
      console.error('Cannot submit: missing question UUID, canvas data, or candidate ID');
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
      }, user.candidateId);
      console.log('Solution submitted successfully');

      // Then end the session to get final report
      try {
        const report = await endSession(questionUuid, user.candidateId);
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
  }, [questionUuid, excalidrawData, user?.candidateId]);

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

