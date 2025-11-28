import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { createSession, getQuestionByUuid, sendChatMessage, updateCanvas } from '../api/systemDesign.api';
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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const sessionCreatedRef = useRef(false);

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
        // Step 1: Create session
        console.log('Creating session...');
        const sessionResponse = await createSession({
          candidate_id: user.candidateId,
        });

        console.log('Session created:', sessionResponse);
        setSessionId(sessionResponse.session_id);

        // Step 2: Fetch question if UUID is available
        if (sessionResponse.question_uuid) {
          console.log('Fetching question with UUID:', sessionResponse.question_uuid);
          const questionResponse = await getQuestionByUuid(sessionResponse.question_uuid);
          
          // Map question response to SystemDesignProblem
          const problemData: SystemDesignProblem = {
            id: 1, // Using 1 as default since backend doesn't provide numeric ID
            title: questionResponse.question_id || 'System Design Problem',
            description: questionResponse.question,
            requirements: questionResponse.evaluation_criteria
              ? questionResponse.evaluation_criteria.split('\n').filter(line => line.trim())
              : [],
          };

          setProblem(problemData);
          console.log('Question loaded:', problemData);
        } else {
          // Fallback: Use question_text from session if no UUID
          console.log('No question UUID, using question_text from session');
          const problemData: SystemDesignProblem = {
            id: 1,
            title: 'System Design Problem',
            description: sessionResponse.question_text,
            requirements: [],
          };
          setProblem(problemData);
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
    if (!sessionId || !excalidrawData) return;

    // Clear existing timeout
    const canvasUpdateTimeout = setTimeout(async () => {
      try {
        await updateCanvas({
          session_id: sessionId,
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
  }, [excalidrawData, sessionId]);

  const handleUpdateNotes = useCallback((newNotes: string) => {
    setNotes(newNotes);
  }, []);

  const handleSendMessage = useCallback(async (message: string) => {
    if (!message.trim() || !sessionId) {
      console.error('Cannot send message: missing session ID');
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
        session_id: sessionId,
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
  }, [sessionId, excalidrawData]);

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
    if (!sessionId || !excalidrawData) {
      console.error('Cannot submit: missing session ID or canvas data');
      return;
    }

    try {
      await updateCanvas({
        session_id: sessionId,
        canvas_data: {
          elements: excalidrawData.elements || [],
          appState: excalidrawData.appState,
          files: excalidrawData.files,
        },
        action: 'submit',
      });
      console.log('Solution submitted successfully');
    } catch (error) {
      console.error('Error submitting solution:', error);
      throw error;
    }
  }, [sessionId, excalidrawData]);

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

