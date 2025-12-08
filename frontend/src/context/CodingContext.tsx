import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { fetchCodingProblems, runCodeExecution, transformInputForLanguage, fixJavaClassName } from '../api/coding.api';
import { useAuth } from './AuthContext';
import type { CodingContextType, CodingProblem } from '../types';

const TIMER_DURATION = 60 * 60; // 60 minutes

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
  const [testResults, setTestResults] = useState<Record<number, Array<{
    input: string;
    expectedOutput: string;
    actualOutput: string | null;
    passed: boolean | null;
  }>>>({});
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(TIMER_DURATION);
  const [isLoading, setIsLoading] = useState(true);

  // Load problems on mount
  useEffect(() => {
    const loadProblems = async () => {
      try {
        const data = await fetchCodingProblems();
        setProblems(data);
        // Initialize code for each problem and language
        const initialCode: Record<string, string> = {};
        data.forEach((problem) => {
          const key = `${problem.id}-python`;
          initialCode[key] = problem.boilerplate.python;
        });
        setCode(initialCode);
        setIsLoading(false);
      } catch (error) {
        console.error('Error loading problems:', error);
        setIsLoading(false);
      }
    };
    loadProblems();
  }, []);

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

  // Load code when switching problems or languages
  useEffect(() => {
    if (!problems.length || currentProblemIndex >= problems.length) return;
    
    const currentProblem = problems[currentProblemIndex];
    const codeKey = `${currentProblem.id}-${selectedLanguage}`;
    
    if (!code[codeKey]) {
      // Initialize with boilerplate if not exists
      setCode((prev) => ({
        ...prev,
        [codeKey]: currentProblem.boilerplate[selectedLanguage]
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
    if (currentProblem) {
      const codeKey = `${currentProblem.id}-${lang}`;
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
    if (currentProblem) {
      const codeKey = `${currentProblem.id}-${selectedLanguage}`;
      setCode((prev) => ({
        ...prev,
        [codeKey]: newCode
      }));
    }
  }, [currentProblemIndex, selectedLanguage, problems]);

  const handleRunCode = useCallback(async () => {
    const currentProblem = problems[currentProblemIndex];
    if (!currentProblem) return;

    // Get user_id from auth context
    const userId = user?.candidateId || 'anonymous';
    
    setIsRunning(true);
    setOutput('Running code...');

    try {
      const codeKey = `${currentProblem.id}-${selectedLanguage}`;
      let currentCode = code[codeKey] || currentProblem.boilerplate[selectedLanguage];
      
      // Fix Java class name issue: remove 'public' keyword from class declaration
      // This prevents "class Result is public, should be declared in a file named Result.java" error
      if (selectedLanguage === 'java') {
        currentCode = fixJavaClassName(currentCode);
      }
      
      // Transform test cases to API format
      // Transform input format based on language requirements
      const sampleTestCases = currentProblem.testCases.map((testCase, index) => ({
        id: `test_${index + 1}`,
        input: transformInputForLanguage(testCase.input, selectedLanguage),
        expected_output: testCase.output
      }));

      // Prepare the request payload
      const requestPayload = {
        language: selectedLanguage,
        code: currentCode,
        sample_test_cases: sampleTestCases,
        user_id: userId,
        question_id: `q${currentProblem.id}`
      };

      // Console log the request being sent to the API
      console.log('Code execution API request (from context):', JSON.stringify(requestPayload, null, 2));

      // Call the code execution API
      const result = await runCodeExecution(requestPayload);

      // Console log the response as requested
      console.log('Code execution API response (from context):', JSON.stringify(result, null, 2));

      // Set output based on summary
      const summaryText = `Tests: ${result.summary.passed}/${result.summary.total_tests} passed (${result.summary.pass_percentage.toFixed(1)}%)`;
      setOutput(summaryText);

      // Map API response to our test results format
      const mappedResults = result.test_results.map((testResult) => ({
        input: testResult.input,
        expectedOutput: testResult.expected_output,
        actualOutput: testResult.actual_output,
        passed: testResult.passed
      }));

      setTestResults((prev) => ({
        ...prev,
        [currentProblem.id]: mappedResults
      }));
    } catch (error) {
      console.error('Error running code:', error);
      setOutput(`Error: ${error instanceof Error ? error.message : 'Failed to run code'}`);
      
      // Set empty test results on error
      setTestResults((prev) => ({
        ...prev,
        [currentProblem.id]: []
      }));
    } finally {
      setIsRunning(false);
    }
  }, [currentProblemIndex, selectedLanguage, problems, code, user?.candidateId]);

  const handleResetCode = useCallback(() => {
    const currentProblem = problems[currentProblemIndex];
    if (currentProblem) {
      const codeKey = `${currentProblem.id}-${selectedLanguage}`;
      setCode((prev) => ({
        ...prev,
        [codeKey]: currentProblem.boilerplate[selectedLanguage]
      }));
    }
  }, [currentProblemIndex, selectedLanguage, problems]);

  const handleGoToProblem = useCallback((index: number) => {
    if (index >= 0 && index < problems.length) {
      setCurrentProblemIndex(index);
    }
  }, [problems.length]);

  const getProgressPercentage = useCallback(() => {
    // Calculate progress based on problems attempted
    const total = problems.length;
    const attempted = Object.keys(code).filter(key => {
      const problemId = parseInt(key.split('-')[0]);
      const problem = problems.find(p => p.id === problemId);
      if (!problem) return false;
      const lang = key.split('-')[1] as 'python' | 'javascript' | 'java' | 'cpp' | 'csharp';
      const codeKey = `${problemId}-${lang}`;
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
    timeRemaining,
    isLoading,
    setLanguage: handleSetLanguage,
    updateCode: handleUpdateCode,
    runCode: handleRunCode,
    resetCode: handleResetCode,
    goToProblem: handleGoToProblem,
    formatTime,
    getProgressPercentage
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

