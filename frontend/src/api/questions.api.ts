import { MOCK_QUESTIONS } from '../utils/constants';
import type { Question } from '../types';
// import { API_BASE_URL } from '../utils/config';

// Get auth token from localStorage
// const getAuthToken = (): string | null => {
//   return localStorage.getItem('auth_token') || localStorage.getItem('google_id_token');
// };

// Backend response types
// interface MCQQuestionResponse {
//   question_uuid: string;
//   question: string;
//   options: string[];
// }

// interface MCQQuestionsResponse {
//   success: boolean;
//   message: string;
//   count: number;
//   questions: MCQQuestionResponse[];
// }

// API functions for fetching questions
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const fetchQuestions = async (_candidateId?: string): Promise<Question[]> => {
  // For now, always return dummy Gen AI questions
  // TODO: Uncomment below code when ready to fetch from backend
  /*
  // If candidateId is provided, fetch from backend
  if (candidateId) {
    try {
      const token = getAuthToken();
      if (!token) {
        throw new Error('Authentication token not found');
      }

      const response = await fetch(`${API_BASE_URL}/candidate/${candidateId}/mcq-questions`, {
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
        id: index + 1, // Use 1-based index as ID
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
  */

  // Return dummy Gen AI questions for now
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_QUESTIONS);
    }, 500);
  });
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const submitAssessment = async (_answers: Record<number, number>): Promise<{ success: boolean; message: string }> => {
  // In a real app, this would submit to backend
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ success: true, message: 'Assessment submitted successfully' });
    }, 1000);
  });
};

