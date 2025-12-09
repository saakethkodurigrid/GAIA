import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { 
  fetchCodingQuestionsFromBackend, 
  runCodeViaBackend, 
  submitCodingAnswer,
  type RunCodeRequest,
  type SubmitCodingAnswerRequest
} from '../api/coding.api';
import { useAuth } from './AuthContext';
import type { CodingContextType, CodingProblem } from '../types';
import { getTestStatus } from '../api/candidate.api';

const TIMER_DURATION = 180 * 60; // 180 minutes (3 hours)

const CodingContext = createContext<CodingContextType | undefined>(undefined);

interface CodingProviderProps {
  children: ReactNode;
}

export const CodingProvider = ({ children }: CodingProviderProps) => {
  const { user } = useAuth();
  const [problems, setProblems] = useState<CodingProblem[]>([]);
  const [currentProblemIndex, setCurrentProblemIndex] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState<'python' | 'javascript' | 'java' | 'cpp' | 'csharp'>('python');
  const [code, setCode] = useState<Record<string, string>>({});
  const [testResults, setTestResults] = useState<Record<string, Array<{
    testCaseId?: string;
    input: string;
    expectedOutput: string;
    actualOutput: string | null;
    passed: boolean | null;
    error: string | null;
    status?: string;
  }>>>({});
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(TIMER_DURATION);
  const [isLoading, setIsLoading] = useState(true);
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<string>>(new Set());
  const [isTimerInitialized, setIsTimerInitialized] = useState(false);

  // Helper function to parse boilerplate code
  // Backend sends boilerplate as JSON string with language keys: {"python": "...", "cpp": "...", ...}
  const parseBoilerplateCode = useCallback((boilerplate: string | null): CodingProblem['boilerplate'] => {
    // Default boilerplate if none provided
    const defaultBoilerplate: CodingProblem['boilerplate'] = {
      python: '# Write your code here\npass',
      javascript: '// Write your code here\n',
      java: '// Write your code here\n',
      cpp: '// Write your code here\n',
      csharp: '// Write your code here\n',
    };

    if (!boilerplate) {
      return defaultBoilerplate;
    }

    try {
      // Try to parse as JSON (backend sends it as JSON string)
      let parsed: Record<string, string>;
      
      // Check if it's already a JSON string or an object
      if (typeof boilerplate === 'string') {
        // Try parsing as JSON
        try {
          parsed = JSON.parse(boilerplate);
        } catch {
          // If parsing fails, treat as plain string and use for Python only
          return {
            ...defaultBoilerplate,
            python: boilerplate,
          };
        }
      } else {
        // Already an object
        parsed = boilerplate as Record<string, string>;
      }

      // Map backend language keys to frontend language keys
      // Backend might use: python, cpp, javascript, java, csharp
      // Also handle variations: c++ → cpp, js → javascript
      const languageMap: Record<string, keyof CodingProblem['boilerplate']> = {
        'python': 'python',
        'cpp': 'cpp',
        'c++': 'cpp',
        'cplusplus': 'cpp',
        'javascript': 'javascript',
        'js': 'javascript',
        'java': 'java',
        'csharp': 'csharp',
        'c#': 'csharp',
      };

      const result: CodingProblem['boilerplate'] = { ...defaultBoilerplate };

      // Map each language from backend to frontend
      Object.keys(parsed).forEach((key) => {
        const normalizedKey = key.toLowerCase().trim();
        const frontendLang = languageMap[normalizedKey];
        
        if (frontendLang && parsed[key]) {
          result[frontendLang] = parsed[key];
        }
      });

      return result;
    } catch (error) {
      console.error('Error parsing boilerplate code:', error);
      // Return default if parsing fails
      return defaultBoilerplate;
    }
  }, []);

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

  // Load problems from backend on mount
  useEffect(() => {
    const loadProblems = async () => {
      if (!user?.candidateId) {
        console.warn('No candidate ID found, cannot load coding questions');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        // Fetch from backend
        const backendQuestions = await fetchCodingQuestionsFromBackend(user.candidateId);
        
        // Transform backend format to frontend format
        const transformedProblems: CodingProblem[] = backendQuestions.map((q, index) => {
          console.log(`=== Parsing boilerplate for question ${index + 1} ===`);
          console.log('Raw boilerplate_code:', q.boilerplate_code);
          console.log('Type:', typeof q.boilerplate_code);
          
          const boilerplate = parseBoilerplateCode(q.boilerplate_code);
          console.log('Parsed boilerplate:', boilerplate);
          console.log('==========================================');
          
          return {
            id: index + 1, // Frontend ID
            question_uuid: q.question_uuid, // Backend UUID for API calls
            title: `Coding Problem ${index + 1}`, // Backend doesn't provide title
            difficulty: 'Medium' as const, // Backend doesn't provide difficulty
            description: q.question,
            examples: q.sample_test_cases.slice(0, 2).map(tc => ({
              input: tc.input,
              output: tc.expected_output,
            })),
            constraints: [], // Backend doesn't provide constraints
            boilerplate: boilerplate,
            testCases: q.sample_test_cases.map(tc => ({
              input: tc.input,
              output: tc.expected_output,
            })),
          };
        });
        
        setProblems(transformedProblems);
        
        // Initialize code for each problem and language
        const initialCode: Record<string, string> = {};
        transformedProblems.forEach((problem) => {
          if (problem.question_uuid) {
            ['python', 'javascript', 'java', 'cpp', 'csharp'].forEach((lang) => {
              const key = `${problem.question_uuid}-${lang}`;
              initialCode[key] = problem.boilerplate[lang as keyof typeof problem.boilerplate] || '';
            });
          }
        });
        setCode(initialCode);
        setIsLoading(false);
      } catch (error) {
        console.error('Error loading coding problems:', error);
        setIsLoading(false);
      }
    };
    
    loadProblems();
  }, [user?.candidateId, parseBoilerplateCode]);

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

  // Load code when switching problems or languages
  useEffect(() => {
    if (!problems.length || currentProblemIndex >= problems.length) return;
    
    const currentProblem = problems[currentProblemIndex];
    if (!currentProblem?.question_uuid) return;
    
    const codeKey = `${currentProblem.question_uuid}-${selectedLanguage}`;
    
    if (!code[codeKey]) {
      // Initialize with boilerplate if not exists
      setCode((prev) => ({
        ...prev,
        [codeKey]: currentProblem.boilerplate[selectedLanguage] || ''
      }));
    }
  }, [currentProblemIndex, selectedLanguage, problems, code]);

  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const handleSetLanguage = useCallback((lang: 'python' | 'javascript' | 'java' | 'cpp' | 'csharp') => {
    setSelectedLanguage(lang);
    const currentProblem = problems[currentProblemIndex];
    if (currentProblem?.question_uuid) {
      const codeKey = `${currentProblem.question_uuid}-${lang}`;
      if (!code[codeKey]) {
        setCode((prev) => ({
          ...prev,
          [codeKey]: currentProblem.boilerplate[lang]
        }));
      }
    }
  }, [currentProblemIndex, problems, code]);

  const handleUpdateCode = useCallback((newCode: string) => {
    const currentProblem = problems[currentProblemIndex];
    if (currentProblem?.question_uuid) {
      const codeKey = `${currentProblem.question_uuid}-${selectedLanguage}`;
      setCode((prev) => ({
        ...prev,
        [codeKey]: newCode
      }));
    }
  }, [currentProblemIndex, selectedLanguage, problems]);

  const handleRunCode = useCallback(async (mode: 'run' | 'run_all' = 'run') => {
    const currentProblem = problems[currentProblemIndex];
    if (!currentProblem || !user?.candidateId) return;

    const questionUuid = currentProblem.question_uuid;
    if (!questionUuid) {
      console.error('Question UUID not found');
      return;
    }

    setIsRunning(true);
    setOutput('Running code...');

    try {
      const codeKey = `${questionUuid}-${selectedLanguage}`;
      const currentCode = code[codeKey] || currentProblem.boilerplate[selectedLanguage];
      
      // Map frontend language to backend language
      // Backend supports: python, javascript, java, cpp, csharp
      // Map csharp to csharp (backend accepts it)
      const backendLanguage = selectedLanguage === 'csharp' 
        ? 'csharp' 
        : selectedLanguage as 'python' | 'javascript' | 'java' | 'cpp' | 'csharp';
      
      const request: RunCodeRequest = {
        question_id: questionUuid,
        language: backendLanguage,
        code: currentCode,
        mode: mode,
      };

      console.log('Running code via backend:', request);

      const result = await runCodeViaBackend(user.candidateId, request);

      // Set output based on summary
      const summaryText = `Tests: ${result.summary.passed}/${result.summary.total_tests} passed (${result.summary.pass_percentage.toFixed(1)}%)`;
      setOutput(summaryText);

      // Map API response to our test results format
      const mappedResults = result.test_results.map((testResult) => ({
        testCaseId: testResult.test_case_id || undefined,
        input: testResult.input || 'Hidden test case',
        expectedOutput: testResult.expected_output || 'Hidden',
        actualOutput: testResult.actual_output || null,
        passed: testResult.passed,
        error: testResult.error || null,
        status: testResult.status || undefined,
      }));

      setTestResults((prev) => ({
        ...prev,
        [questionUuid]: mappedResults
      }));
    } catch (error) {
      console.error('Error running code:', error);
      setOutput(`Error: ${error instanceof Error ? error.message : 'Failed to run code'}`);
      
      setTestResults((prev) => ({
        ...prev,
        [questionUuid]: [] as Array<{
          input: string;
          expectedOutput: string;
          actualOutput: string | null;
          passed: boolean | null;
          error: string | null;
          status?: string;
        }>
      }));
    } finally {
      setIsRunning(false);
    }
  }, [currentProblemIndex, selectedLanguage, problems, code, user?.candidateId]);

  // Add new function for running all test cases
  const handleRunAllTestCases = useCallback(async () => {
    await handleRunCode('run_all');
  }, [handleRunCode]);

  // Helper function to find next unsubmitted question
  const findNextUnsubmittedQuestion = useCallback((currentIndex: number): number | null => {
    // Start searching from the next question
    for (let i = currentIndex + 1; i < problems.length; i++) {
      const problem = problems[i];
      if (problem?.question_uuid && !submittedQuestions.has(problem.question_uuid)) {
        return i;
      }
    }
    // If no unsubmitted question found after current, search from beginning
    for (let i = 0; i < currentIndex; i++) {
      const problem = problems[i];
      if (problem?.question_uuid && !submittedQuestions.has(problem.question_uuid)) {
        return i;
      }
    }
    // All questions are submitted
    return null;
  }, [problems, submittedQuestions]);

  // Helper function to check if all questions are submitted
  const areAllQuestionsSubmitted = useCallback((): boolean => {
    if (problems.length === 0) return false;
    return problems.every(problem => 
      problem?.question_uuid && submittedQuestions.has(problem.question_uuid)
    );
  }, [problems, submittedQuestions]);

  // Add new function for submitting answer
  const handleSubmitAnswer = useCallback(async (): Promise<boolean> => {
    const currentProblem = problems[currentProblemIndex];
    if (!currentProblem || !user?.candidateId) return false;

    const questionUuid = currentProblem.question_uuid;
    if (!questionUuid) {
      console.error('Question UUID not found');
      return false;
    }

    // Prevent duplicate submission
    if (submittedQuestions.has(questionUuid)) {
      console.warn('Question already submitted');
      setOutput('This question has already been submitted.');
      return false;
    }

    // Mark question as submitted immediately (optimistic update)
    setSubmittedQuestions((prev) => new Set([...prev, questionUuid]));
    setOutput('Submitting answer...');

    // Prepare submission data
    const codeKey = `${questionUuid}-${selectedLanguage}`;
    const currentCode = code[codeKey] || currentProblem.boilerplate[selectedLanguage];
    
    // Map frontend language to backend language
    const backendLanguage = selectedLanguage as 'python' | 'javascript' | 'java' | 'cpp' | 'csharp';
    
    const request: SubmitCodingAnswerRequest = {
      question_id: questionUuid,
      language: backendLanguage,
      code: currentCode,
    };

    console.log('Submitting answer via backend (background):', request);

    // Fire API call in background without waiting
    submitCodingAnswer(user.candidateId, request)
      .then((result) => {
        setOutput(
          `Submitted! Score: ${result.score} | ` +
          `Passed: ${result.test_cases_passed}/${result.total_test_cases} ` +
          `(Sample: ${result.sample_test_cases_passed}, Hidden: ${result.hidden_test_cases_passed})`
        );
        console.log('Submission successful:', result);
      })
      .catch((error) => {
        console.error('Error submitting answer (background):', error);
        // Optionally revert the optimistic update on error
        // For now, we'll keep it submitted but log the error
        setOutput(`Submission in progress. Error: ${error instanceof Error ? error.message : 'Failed to submit answer'}`);
      });

    // Return immediately without waiting for API response
    return true;
  }, [currentProblemIndex, selectedLanguage, problems, code, user?.candidateId, submittedQuestions]);

  const handleResetCode = useCallback(() => {
    const currentProblem = problems[currentProblemIndex];
    if (currentProblem?.question_uuid) {
      const codeKey = `${currentProblem.question_uuid}-${selectedLanguage}`;
      setCode((prev) => ({
        ...prev,
        [codeKey]: currentProblem.boilerplate[selectedLanguage]
      }));
    }
  }, [currentProblemIndex, selectedLanguage, problems]);

  const handleGoToProblem = useCallback((index: number) => {
    if (index >= 0 && index < problems.length) {
      const problem = problems[index];
      // Prevent navigation to submitted questions
      if (problem?.question_uuid && submittedQuestions.has(problem.question_uuid)) {
        return;
      }
      setCurrentProblemIndex(index);
    }
  }, [problems, submittedQuestions]);

  const getProgressPercentage = useCallback(() => {
    // Calculate progress based on problems attempted
    const total = problems.length;
    const attempted = Object.keys(code).filter(key => {
      const [questionUuid] = key.split('-');
      const problem = problems.find(p => p.question_uuid === questionUuid);
      if (!problem) return false;
      const lang = key.split('-')[1] as 'python' | 'javascript' | 'java' | 'cpp' | 'csharp';
      const codeKey = `${questionUuid}-${lang}`;
      const currentCode = code[codeKey] || problem.boilerplate[lang];
      return currentCode !== problem.boilerplate[lang];
    }).length;
    return total > 0 ? (attempted / total) * 100 : 0;
  }, [problems, code]);

  const value: CodingContextType = {
    problems,
    currentProblemIndex,
    currentProblem: problems[currentProblemIndex],
    selectedLanguage,
    code,
    testResults,
    output,
    isRunning,
    isSubmitting,
    timeRemaining,
    isLoading,
    submittedQuestions,
    setLanguage: handleSetLanguage,
    updateCode: handleUpdateCode,
    runCode: () => handleRunCode('run'), // Default to sample test cases
    runAllTestCases: handleRunAllTestCases, // New function
    submitAnswer: handleSubmitAnswer, // New function
    resetCode: handleResetCode,
    goToProblem: handleGoToProblem,
    formatTime,
    getProgressPercentage,
    findNextUnsubmittedQuestion,
    areAllQuestionsSubmitted
  };

  return <CodingContext.Provider value={value}>{children}</CodingContext.Provider>;
};

export const useCoding = (): CodingContextType => {
  const context = useContext(CodingContext);
  if (!context) {
    throw new Error('useCoding must be used within CodingProvider');
  }
  return context;
};

