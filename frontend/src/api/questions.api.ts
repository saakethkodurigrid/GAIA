import { MOCK_QUESTIONS } from '../utils/constants';
import type { Question } from '../types';
import { API_BASE_URL } from '../utils/config';

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

      console.log('=== Fetching MCQ Questions ===');
      console.log('Using candidate_id:', finalCandidateId);
      console.log('==============================');

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
      
      console.log('=== MCQ QUESTIONS RESPONSE FROM BACKEND ===');
      console.log('Full Response:', JSON.stringify(data, null, 2));
      console.log('Success:', data.success);
      console.log('Message:', data.message);
      console.log('Count:', data.count);
      console.log('Questions:', data.questions);
      console.log('==========================================');
      
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

      return mappedQuestions;
    } catch (error) {
      console.error('Error fetching questions from backend:', error);
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

interface SaveMCQAnswerResponse {
  success: boolean;
  message: string;
  saved_count: number;
  failed_count: number;
  failed_questions: string[];
  total_score: number;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
}

export const submitAssessment = async (
  answers: Record<number, number>,
  questions: Question[],
  candidateId?: string
): Promise<SaveMCQAnswerResponse> => {
  // Use provided candidateId or get from localStorage
  const finalCandidateId = candidateId || getCandidateId();
  if (!finalCandidateId) {
    throw new Error('Candidate ID is required. Please access the page using the invitation link.');
  }

  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication token not found');
  }

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

  if (answerItems.length === 0) {
    throw new Error('No answers to submit');
  }

  const requestBody = {
    answers: answerItems,
  };

  // Log request body being sent to backend
  console.log('=== MCQ SUBMISSION REQUEST (FRONTEND) ===');
  console.log('Using candidate_id:', finalCandidateId);
  console.log('URL:', `${API_BASE_URL}/candidate/${finalCandidateId}/mcq-questions/save-answers`);
  console.log('Request Body:', JSON.stringify(requestBody, null, 2));
  console.log('Number of answers:', answerItems.length);
  console.log('==========================================');

  const response = await fetch(
    `${API_BASE_URL}/candidate/${finalCandidateId}/mcq-questions/save-answers`,
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

  const data: SaveMCQAnswerResponse = await response.json();
  return data;
};

