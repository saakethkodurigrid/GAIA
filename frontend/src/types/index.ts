export interface Question {
  id: number;
  topic: string;
  question: string;
  options: string[];
  correctAnswer: number;
}

export interface MCQContextType {
  questions: Question[];
  currentQuestionIndex: number;
  currentQuestion: Question | undefined;
  answers: Record<number, number>;
  savedAnswers: Record<number, number>;
  questionStatuses: Record<number, string>;
  timeRemaining: number;
  isLoading: boolean;
  selectAnswer: (questionId: number, answerIndex: number) => void;
  clearSelection: (questionId: number) => void;
  markForReview: (questionId: number) => void;
  saveAnswer: (questionId: number) => void;
  goToQuestion: (index: number) => void;
  goToNext: () => void;
  goToPrevious: () => void;
  saveAndNext: () => void;
  goToNextOnly: () => void;
  hasUnsavedChanges: () => boolean;
  getStatusCounts: () => Record<string, number>;
  getProgressPercentage: () => number;
  formatTime: (seconds: number) => string;
}

export interface SubmitSectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (answers: Record<number, number>) => void;
}

export interface CodingProblem {
  id: number;
  title: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  description: string;
  examples: Array<{
    input: string;
    output: string;
    explanation?: string;
  }>;
  constraints: string[];
  boilerplate: {
    python: string;
    javascript: string;
    java: string;
  };
  testCases: Array<{
    input: string;
    output: string;
  }>;
}

export interface CodingContextType {
  problems: CodingProblem[];
  currentProblemIndex: number;
  currentProblem: CodingProblem | undefined;
  selectedLanguage: 'python' | 'javascript' | 'java';
  code: Record<string, string>;
  testResults: Record<number, Array<{
    input: string;
    expectedOutput: string;
    actualOutput: string | null;
    passed: boolean | null;
  }>>;
  output: string;
  isRunning: boolean;
  timeRemaining: number;
  isLoading: boolean;
  setLanguage: (lang: 'python' | 'javascript' | 'java') => void;
  updateCode: (code: string) => void;
  runCode: () => Promise<void>;
  resetCode: () => void;
  goToProblem: (index: number) => void;
  formatTime: (seconds: number) => string;
  getProgressPercentage: () => number;
}

export interface SystemDesignProblem {
  id: number;
  title: string;
  description: string;
  requirements: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface SystemDesignContextType {
  problem: SystemDesignProblem | null;
  excalidrawData: any;
  notes: string;
  chatMessages: ChatMessage[];
  timeRemaining: number;
  isLoading: boolean;
  updateExcalidrawData: (data: any) => void;
  updateNotes: (notes: string) => void;
  sendMessage: (message: string) => Promise<void>;
  clearCanvas: (excalidrawAPI?: any) => void;
  formatTime: (seconds: number) => string;
  submitSolution: () => Promise<void>;
}

// Auth Types
export type UserType = 'admin' | 'recruiter' | 'candidate';
export type CandidateStatus = 'registered' | 'scheduled' | 'ongoing' | 'done';

export interface GoogleTokenRequest {
  token: string;
}

export interface CandidateLoginRequest {
  token: string;
  candidate_id: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user_type?: UserType;
  email?: string;
  name?: string;
  status?: CandidateStatus;
  candidate_id?: string;
  redirect_url?: string;
  id_token?: string;  // Google ID token for API authentication
}

export interface GoogleAuthURLResponse {
  auth_url: string;
  state?: string;
}

export interface AuthContextType {
  isAuthenticated: boolean;
  user: {
    email?: string;
    name?: string;
    userType?: UserType;
    status?: CandidateStatus;
    candidateId?: string;
  } | null;
  isLoading: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => void;
  clearError: () => void;
}
