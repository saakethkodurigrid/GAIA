import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { fetchQuestions } from '../api/questions.api';
import { QUESTION_STATUS, TIMER_DURATION } from '../utils/constants';
import type { MCQContextType, Question } from '../types';
import { useAuth } from './AuthContext';
import { sendHeartbeat, getTestStatus } from '../api/candidate.api';
import { submitAssessment } from '../api/questions.api';

const MCQContext = createContext<MCQContextType | undefined>(undefined);

interface MCQProviderProps {
  children: ReactNode;
}

const STORAGE_KEY = 'mcq_answers';

// Helper functions for localStorage
const loadAnswersFromStorage = (): Record<number, number | null> => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Convert string keys to numbers and handle null values
      const result: Record<number, number | null> = {};
      Object.keys(parsed).forEach((key) => {
        const questionId = parseInt(key, 10);
        result[questionId] = parsed[key] === null ? null : parsed[key];
      });
      return result;
    }
  } catch (error) {
    console.error('Error loading answers from localStorage:', error);
  }
  return {};
};

const saveAnswersToStorage = (answers: Record<number, number | null>) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
  } catch (error) {
    console.error('Error saving answers to localStorage:', error);
  }
};

export const MCQProvider = ({ children }: MCQProviderProps) => {
  const { user } = useAuth();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [savedAnswers, setSavedAnswers] = useState<Record<number, number>>({});
  const [questionStatuses, setQuestionStatuses] = useState<Record<number, string>>({});
  const [timeRemaining, setTimeRemaining] = useState(TIMER_DURATION);
  const [isLoading, setIsLoading] = useState(true);
  const [isTimerInitialized, setIsTimerInitialized] = useState(false);

  // Sync timer from backend on mount
  useEffect(() => {
    const syncTimer = async () => {
      const candidateId = user?.candidateId;
      if (!candidateId) return;

      try {
        const status = await getTestStatus(candidateId);
        if (status.success && status.status === 'active' && status.remaining_seconds >= 0) {
          setTimeRemaining(status.remaining_seconds);
          setIsTimerInitialized(true);
        } else {
          setIsTimerInitialized(true);
        }
      } catch (error) {
        console.error('Failed to sync timer from backend:', error);
        // Continue with local timer if backend sync fails
        setIsTimerInitialized(true);
      }
    };

    syncTimer();

    // Sync every 30 seconds to account for any drift
    const syncInterval = setInterval(syncTimer, 30000);

    return () => clearInterval(syncInterval);
  }, [user?.candidateId]);

  // Load questions on mount and initialize from localStorage
  useEffect(() => {
    const loadQuestions = async () => {
      try {
        const candidateId = user?.candidateId;
        if (!candidateId) return;

        // Fetch questions (will come from Redis if test was started, otherwise from DB)
        const data = await fetchQuestions(candidateId);
        setQuestions(data);
        
        // Load saved answers from localStorage
        const storedAnswers = loadAnswersFromStorage();
        const loadedSavedAnswers: Record<number, number> = {};
        const initialStatuses: Record<number, string> = {};
        
        data.forEach((q) => {
          const storedAnswer = storedAnswers[q.id];
          if (storedAnswer !== null && storedAnswer !== undefined) {
            loadedSavedAnswers[q.id] = storedAnswer;
            initialStatuses[q.id] = QUESTION_STATUS.ANSWERED;
          } else {
            initialStatuses[q.id] = QUESTION_STATUS.NOT_ANSWERED;
          }
        });
        
        setSavedAnswers(loadedSavedAnswers);
        setQuestionStatuses(initialStatuses);
        setIsLoading(false);
      } catch (error) {
        console.error('Error loading questions:', error);
        setIsLoading(false);
      }
    };
    loadQuestions();
  }, [user?.candidateId]);

  // Initialize current question's answer from savedAnswers when questions load
  useEffect(() => {
    if (questions.length > 0 && currentQuestionIndex < questions.length) {
      const currentQuestion = questions[currentQuestionIndex];
      if (currentQuestion && savedAnswers[currentQuestion.id] !== undefined && answers[currentQuestion.id] === undefined) {
        setAnswers((prev) => ({
          ...prev,
          [currentQuestion.id]: savedAnswers[currentQuestion.id]
        }));
      }
    }
  }, [questions.length, currentQuestionIndex]); // Only run when questions load or index changes

  // Timer countdown (only start after initial sync)
  useEffect(() => {
    if (!isTimerInitialized || timeRemaining <= 0) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isTimerInitialized, timeRemaining]);

  // Heartbeat interval - send every 2 minutes to keep test session alive
  useEffect(() => {
    const candidateId = user?.candidateId;
    if (!candidateId || timeRemaining <= 0 || isLoading) return;

    // Send heartbeat every 2 minutes (120 seconds)
    const heartbeatInterval = setInterval(async () => {
      try {
        const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
        if (token && candidateId) {
          await sendHeartbeat(candidateId, token);
          console.log('Heartbeat sent successfully');
        }
      } catch (error) {
        console.error('Failed to send heartbeat:', error);
        // Don't throw - heartbeat failure shouldn't break the test
      }
    }, 120000); // 2 minutes

    return () => clearInterval(heartbeatInterval);
  }, [user?.candidateId, timeRemaining, isLoading]);

  // Auto-save answers to Redis every 30 seconds
  useEffect(() => {
    const candidateId = user?.candidateId;
    if (!candidateId || questions.length === 0 || isLoading) return;

    const autoSaveInterval = setInterval(async () => {
      // Check if there are unsaved answers
      const hasUnsaved = Object.keys(answers).some(
        (qId) => {
          const questionId = parseInt(qId);
          return answers[questionId] !== undefined && 
                 answers[questionId] !== savedAnswers[questionId];
        }
      );

      if (hasUnsaved) {
        try {
          const token = localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
          if (token && candidateId) {
            // Convert to backend format
            const answerItems = questions
              .filter((q) => {
                const answer = answers[q.id];
                return answer !== undefined && answer !== null && q.question_uuid;
              })
              .map((q) => ({
                question_uuid: q.question_uuid!,
                candidate_answer: String(answers[q.id]),
              }));

            if (answerItems.length > 0) {
              await submitAssessment(answers, questions, candidateId);
              console.log('Auto-saved answers to Redis');
            }
          }
        } catch (error) {
          console.error('Auto-save failed:', error);
          // Silent fail - don't interrupt user experience
        }
      }
    }, 30000); // 30 seconds

    return () => clearInterval(autoSaveInterval);
  }, [user?.candidateId, answers, savedAnswers, questions, isLoading]);

  const selectAnswer = useCallback((questionId: number, answerIndex: number) => {
    // Only update the selected answer, don't automatically save or change status
    setAnswers((prev) => ({
      ...prev,
      [questionId]: answerIndex
    }));
  }, []);

  const clearSelection = useCallback((questionId: number) => {
    // Clear the selected answer for the current question
    setAnswers((prev) => {
      const newAnswers = { ...prev };
      delete newAnswers[questionId];
      return newAnswers;
    });
    
    // Also remove from savedAnswers and update localStorage
    setSavedAnswers((prev) => {
      const newSavedAnswers = { ...prev };
      delete newSavedAnswers[questionId];
      
      // Update localStorage
      const allAnswers: Record<number, number | null> = {};
      questions.forEach((q) => {
        allAnswers[q.id] = newSavedAnswers[q.id] !== undefined ? newSavedAnswers[q.id] : null;
      });
      saveAnswersToStorage(allAnswers);
      
      return newSavedAnswers;
    });
    
    // Update status
    setQuestionStatuses((prev) => ({
      ...prev,
      [questionId]: QUESTION_STATUS.NOT_ANSWERED
    }));
  }, [questions]);

  const markForReview = useCallback((questionId: number) => {
    setQuestionStatuses((prev) => ({
      ...prev,
      [questionId]: QUESTION_STATUS.MARKED
    }));
  }, []);

  const saveAnswer = useCallback((questionId: number) => {
    if (answers[questionId] !== undefined) {
      // Save the answer
      const newSavedAnswers = {
        ...savedAnswers,
        [questionId]: answers[questionId]
      };
      setSavedAnswers(newSavedAnswers);
      setQuestionStatuses((prev) => ({
        ...prev,
        [questionId]: QUESTION_STATUS.ANSWERED
      }));
      
      // Save to localStorage
      const allAnswers: Record<number, number | null> = {};
      questions.forEach((q) => {
        allAnswers[q.id] = newSavedAnswers[q.id] !== undefined ? newSavedAnswers[q.id] : null;
      });
      saveAnswersToStorage(allAnswers);
    }
  }, [answers, savedAnswers, questions]);

  const goToQuestion = useCallback((index: number) => {
    if (index >= 0 && index < questions.length) {
      setCurrentQuestionIndex(index);
      // Initialize selected answer from saved answer if available
      const question = questions[index];
      if (question && savedAnswers[question.id] !== undefined && answers[question.id] === undefined) {
        setAnswers((prev) => ({
          ...prev,
          [question.id]: savedAnswers[question.id]
        }));
      }
    }
  }, [questions, savedAnswers, answers]);

  const goToNext = useCallback(() => {
    if (currentQuestionIndex < questions.length - 1) {
      const nextIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(nextIndex);
      // Initialize selected answer from saved answer if available
      const question = questions[nextIndex];
      if (question && savedAnswers[question.id] !== undefined && answers[question.id] === undefined) {
        setAnswers((prev) => ({
          ...prev,
          [question.id]: savedAnswers[question.id]
        }));
      }
    }
  }, [currentQuestionIndex, questions, savedAnswers, answers]);

  const goToPrevious = useCallback(() => {
    if (currentQuestionIndex > 0) {
      const prevIndex = currentQuestionIndex - 1;
      setCurrentQuestionIndex(prevIndex);
      // Initialize selected answer from saved answer if available
      const question = questions[prevIndex];
      if (question && savedAnswers[question.id] !== undefined && answers[question.id] === undefined) {
        setAnswers((prev) => ({
          ...prev,
          [question.id]: savedAnswers[question.id]
        }));
      }
    }
  }, [currentQuestionIndex, questions, savedAnswers, answers]);

  const saveAndNext = useCallback(() => {
    const currentQuestion = questions[currentQuestionIndex];
    if (currentQuestion && answers[currentQuestion.id] !== undefined) {
      saveAnswer(currentQuestion.id);
    }
    goToNext();
  }, [currentQuestionIndex, questions, answers, saveAnswer, goToNext]);

  const goToNextOnly = useCallback(() => {
    goToNext();
  }, [goToNext]);

  // Check if current question has unsaved changes
  const hasUnsavedChanges = useCallback(() => {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return false;
    const selected = answers[currentQuestion.id];
    const saved = savedAnswers[currentQuestion.id];
    return selected !== undefined && selected !== saved;
  }, [currentQuestionIndex, questions, answers, savedAnswers]);

  const getStatusCounts = useCallback(() => {
    const counts: Record<string, number> = {
      [QUESTION_STATUS.ANSWERED]: 0,
      [QUESTION_STATUS.MARKED]: 0,
      [QUESTION_STATUS.NOT_ANSWERED]: 0
    };

    Object.values(questionStatuses).forEach((status) => {
      counts[status] = (counts[status] || 0) + 1;
    });

    return counts;
  }, [questionStatuses]);

  const getProgressPercentage = useCallback(() => {
    const counts = getStatusCounts();
    const total = questions.length;
    const answered = counts[QUESTION_STATUS.ANSWERED];
    return total > 0 ? (answered / total) * 100 : 0;
  }, [questions.length, getStatusCounts]);

  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const value: MCQContextType = {
    questions,
    currentQuestionIndex,
    currentQuestion: questions[currentQuestionIndex],
    answers,
    savedAnswers,
    questionStatuses,
    timeRemaining,
    isLoading,
    selectAnswer,
    clearSelection,
    markForReview,
    saveAnswer,
    goToQuestion,
    goToNext,
    goToPrevious,
    saveAndNext,
    goToNextOnly,
    hasUnsavedChanges,
    getStatusCounts,
    getProgressPercentage,
    formatTime
  };

  return <MCQContext.Provider value={value}>{children}</MCQContext.Provider>;
};

export const useMCQ = (): MCQContextType => {
  const context = useContext(MCQContext);
  if (!context) {
    throw new Error('useMCQ must be used within MCQProvider');
  }
  return context;
};

