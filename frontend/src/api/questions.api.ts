import { MOCK_QUESTIONS } from '../utils/constants';
import type { Question } from '../types';
import { API_BASE_URL } from '../utils/config';
import { logger } from '../utils/logger';

// Get auth token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
};

// Get candidate_id from localStorage
const getCandidateId = (): string | null => {
  return localStorage.getItem('current_candidate_id');
};

// Backend response types
interface MCQQuestionResponse {
  question_uuid: string;
  question: string;
  options: string[];
}

interface MCQQuestionsResponse {
  success: boolean;
  message: string;
  count: number;
  questions: MCQQuestionResponse[];
}

// API functions for fetching questions
export const fetchQuestions = async (candidateId?: string): Promise<Question[]> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  
  // If candidateId is available, fetch from backend
  if (finalCandidateId) {
    try {
      const token = getAuthToken();
      if (!token) {
        throw new Error('Authentication token not found');
      }

      logger.log('=== Fetching MCQ Questions ===');
      logger.log('Using candidate_id:', finalCandidateId);
      logger.log('==============================');

      const response = await fetch(`${API_BASE_URL}/candidate/${finalCandidateId}/mcq-questions`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to fetch questions' }));
        throw new Error(error.detail || 'Failed to fetch questions');
      }

      const data: MCQQuestionsResponse = await response.json();
      
      logger.log('=== MCQ QUESTIONS RESPONSE FROM BACKEND ===');
      logger.log('Full Response:', JSON.stringify(data, null, 2));
      logger.log('Success:', data.success);
      logger.log('Message:', data.message);
      logger.log('Count:', data.count);
      logger.log('Questions:', data.questions);
      logger.log('==========================================');
      
      if (!data.success || !data.questions) {
        throw new Error(data.message || 'Failed to fetch questions');
      }

      // Limit to 25 questions
      const limitedQuestions = data.questions.slice(0, 25);

      // Map backend response to frontend Question format
      const mappedQuestions: Question[] = limitedQuestions.map((q, index) => ({
        id: index + 1, // Use 1-based index as ID for frontend
        question_uuid: q.question_uuid, // Preserve UUID from backend for submission
        topic: '', // Backend doesn't provide topic
        question: q.question,
        options: q.options,
        correctAnswer: -1, // Backend doesn't provide correct answer
      }));

      logger.log('=== SUCCESSFULLY MAPPED QUESTIONS ===');
      logger.log('Mapped questions count:', mappedQuestions.length);
      logger.log('First mapped question:', mappedQuestions[0]);
      logger.log('All have question_uuid?', mappedQuestions.every(q => q.question_uuid));
      logger.log('===================================');
      
      return mappedQuestions;
    } catch (error) {
      logger.error('❌ ERROR fetching questions from backend:', error);
      logger.warn('⚠️ FALLING BACK TO MOCK_QUESTIONS - THESE WILL NOT HAVE question_uuid!');
      logger.warn('⚠️ SUBMISSION WILL FAIL WITH MOCK DATA!');
      // Fallback to mock data on error
      return MOCK_QUESTIONS;
    }
  }

  // Return dummy Gen AI questions for now if no candidateId
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_QUESTIONS);
    }, 500);
  });
};

// Backend request/response types for submission
interface MCQAnswerItem {
  question_uuid: string;
  candidate_answer: string; // Option number as string (e.g., "1", "2", "3", "4")
}

interface AutosaveMCQAnswerResponse {
  success: boolean;
  message: string;
  saved_count: number;
  last_updated_at: string;
}

interface SubmitMCQAnswerResponse {
  success: boolean;
  message: string;
  saved_count: number;
  failed_count: number;
  failed_questions: string[];
  total_score: number;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  submitted_at: string;
}

export const autosaveAssessment = async (
  answers: Record<number, number>,
  questions: Question[],
  candidateId?: string
): Promise<AutosaveMCQAnswerResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found');
  }

  // DEBUG: Log what we received for autosave
  logger.log('[AUTOSAVE] answers object:', Object.keys(answers).length, 'keys');
  logger.log('[AUTOSAVE] questions array:', questions.length, 'questions');
  
  // Convert frontend answers format to backend format
  const answerItems: MCQAnswerItem[] = questions
    .filter((q) => {
      // Only include questions that have an answer and a question_uuid
      const answer = answers[q.id];
      return answer !== undefined && answer !== null && q.question_uuid;
    })
    .map((q) => {
      const answer = answers[q.id];
      // Convert 0-based index to 1-based option number (frontend stores 0,1,2,3 but backend expects 1,2,3,4)
      return {
        question_uuid: q.question_uuid!,
        candidate_answer: String(answer + 1), // Add 1 to convert from 0-based to 1-based
      };
    });

  logger.log('[AUTOSAVE] Prepared', answerItems.length, 'answers for autosave');

  const requestBody = {
    answers: answerItems,
  };

  // Fire-and-forget: don't block UI, don't await response
  fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/mcq-questions/autosave`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    }
  )
    .then((response) => {
      if (!response.ok) {
        logger.warn('Autosave failed:', response.status);
      } else {
        logger.log('Autosave successful');
      }
    })
    .catch((error) => {
      logger.warn('Autosave error (non-blocking):', error);
    });

  // Return immediately with success (fire-and-forget)
  return {
    success: true,
    message: 'Autosave initiated',
    saved_count: answerItems.length,
    last_updated_at: new Date().toISOString(),
  };
};

export const submitAssessment = async (
  answers: Record<number, number>,
  questions: Question[],
  candidateId?: string
): Promise<SubmitMCQAnswerResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found');
  }

  // DEBUG: Log what we received
  logger.log('=== submitAssessment DEBUG ===');
  logger.log('Received answers object:', answers);
  logger.log('Received questions array length:', questions.length);
  logger.log('First question sample:', questions[0]);
  logger.log('============================');

  // CRITICAL CHECK: Verify questions have question_uuid
  const questionsWithoutUuid = questions.filter(q => !q.question_uuid);
  if (questionsWithoutUuid.length > 0) {
    logger.error('❌ CRITICAL ERROR: Questions missing question_uuid!');
    logger.error(`${questionsWithoutUuid.length} out of ${questions.length} questions don't have question_uuid`);
    logger.error('First question without UUID:', questionsWithoutUuid[0]);
    logger.error('This means questions were likely loaded from MOCK_QUESTIONS or backend is not returning question_uuid');
    logger.error('SUBMISSION WILL FAIL!');
  }

  // Convert frontend answers format to backend format
  const answerItems: MCQAnswerItem[] = questions
    .filter((q) => {
      // Only include questions that have an answer and a question_uuid
      const answer = answers[q.id];
      const hasAnswer = answer !== undefined && answer !== null;
      const hasUuid = !!q.question_uuid;
      
      // DEBUG: Log filtering decision for each question
      if (!hasAnswer || !hasUuid) {
        logger.log(`Question ${q.id} filtered out: hasAnswer=${hasAnswer} (value=${answer}), hasUuid=${hasUuid}`);
      }
      
      return hasAnswer && hasUuid;
    })
    .map((q) => {
      const answer = answers[q.id];
      // Convert 0-based index to 1-based option number (frontend stores 0,1,2,3 but backend expects 1,2,3,4)
      const mapped = {
        question_uuid: q.question_uuid!,
        candidate_answer: String(answer + 1), // Add 1 to convert from 0-based to 1-based
      };
      logger.log(`Mapping Q${q.id}: answer=${answer} -> candidate_answer=${mapped.candidate_answer}, uuid=${mapped.question_uuid}`);
      return mapped;
    });

  const requestBody = {
    answers: answerItems,
  };

  // Log request body being sent to backend
  logger.log('=== MCQ SUBMISSION REQUEST (FRONTEND) ===');
  logger.log('Using candidate_id:', finalCandidateId);
  logger.log('URL:', `${API_BASE_URL}/candidate/${finalCandidateId}/mcq-questions/submit`);
  logger.log('Request Body:', JSON.stringify(requestBody, null, 2));
  logger.log('Number of answers:', answerItems.length);
  logger.log('==========================================');

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/mcq-questions/submit`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to submit answers' }));
    throw new Error(error.detail || 'Failed to submit answers');
  }

  const data: SubmitMCQAnswerResponse = await response.json();
  return data;
};

