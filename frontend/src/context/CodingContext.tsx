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
import { localStorage as storage } from '../utils/localStorage';

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
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<string>>(new Set());
  const [isTimerInitialized, setIsTimerInitialized] = useState(false);

  // Helper function to normalize constraint text (convert "10 5" to "10^5", "109" to "10^9", etc.)
  const normalizeConstraintText = useCallback((text: string): string => {
    // First, handle cases where "10" and exponent are separated by space: "10 5" -> "10^5"
    let normalized = text.replace(/(\b10)\s+(\d{1,2})\b/g, (_match, base, exp) => {
      // Convert "10 5" to "10^5", "10 9" to "10^9", etc.
      return `${base}^${exp}`;
    });
    
    // Then handle cases where "10" and exponent are together: "109" -> "10^9", "105" -> "10^5"
    // Pattern: "10" followed by 1-2 digits that could be an exponent (typically 1-9, 10-99)
    normalized = normalized.replace(/\b10(\d{1,2})\b/g, (match, exp) => {
      const expNum = parseInt(exp, 10);
      // Only convert if it looks like exponent notation (typically 1-99, but prioritize common ones like 5, 9)
      if (expNum >= 1 && expNum <= 99) {
        // Check if the number after "10" makes sense as an exponent
        // Common exponents: 5, 9, 6, 4, 3, 2, etc.
        return `10^${exp}`;
      }
      return match;
    });
    
    return normalized.trim();
  }, []);

  // Helper function to parse question HTML/text to extract title, description, and constraints
  const parseQuestionText = useCallback((questionText: string): { title: string; description: string; constraints: string[] } => {
    if (!questionText) {
      return { title: '', description: '', constraints: [] };
    }

    // Create a temporary DOM element to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = questionText;

    // Extract title - look for h1, h2, h3, or strong tags
    let title = '';
    const titleSelectors = ['h1', 'h2', 'h3', 'h4', 'strong', 'b'];
    for (const selector of titleSelectors) {
      const titleElement = tempDiv.querySelector(selector);
      if (titleElement && titleElement.textContent && titleElement.textContent.trim().length > 0) {
        title = titleElement.textContent.trim();
        break;
      }
    }

    // Extract constraints - look for sections with "Constraints" heading
    const constraints: string[] = [];
    let constraintsHeading: Element | null = null;
    const fullText = tempDiv.textContent || questionText;
    
    // Method 1: Look for "Constraints" text in the full text (most reliable)
    const constraintSectionMatch = fullText.match(/(?:constraints?:?)\s*(.+?)(?=\n\n|\n[A-Z][a-z]{2,}|$)/is);
    if (constraintSectionMatch && constraintSectionMatch[1]) {
      const constraintText = constraintSectionMatch[1].trim();
      
      // Split constraints by looking for patterns that start with numbers followed by operators
      // Pattern: number followed by ≤ or < or > or =, then variable/text, then ≤ or < or > or =, then number/exponent
      // This matches patterns like "1 ≤ n ≤ 10^5", "1 < capacity[i] < 10^6", etc.
      // First, normalize the text to convert "10 5" to "10^5" and "109" to "10^9"
      const normalizedText = normalizeConstraintText(constraintText);
      
      // Pattern to match complete constraints: "1 ≤ variable ≤ 10^5" or similar
      // Matches: number, operator, variable (can include brackets), operator, number/exponent
      const constraintPattern = /(\d+\s+[≤<>=]\s+[^\d≤<>=]+\s+[≤<>=]\s+[^\s]+(?:\^?\d+)?)/g;
      const constraintMatches = normalizedText.match(constraintPattern);
      
      if (constraintMatches && constraintMatches.length > 0) {
        // Found individual constraints - each match is a separate constraint
        constraintMatches.forEach(match => {
          const trimmed = match.trim();
          if (trimmed.length > 0) {
            constraints.push(trimmed);
          }
        });
        
        // Check if there's any remaining text after the last constraint (like "It is guaranteed...")
        const lastMatch = constraintMatches[constraintMatches.length - 1];
        const lastIndex = normalizedText.lastIndexOf(lastMatch) + lastMatch.length;
        const remainingText = normalizedText.substring(lastIndex).trim();
        if (remainingText.length > 0 && !remainingText.match(/^\d+\s+[≤<>=]/)) {
          // This is likely a guarantee or additional constraint text
          constraints.push(remainingText);
        }
      } else {
        // Fallback: Split by looking for number patterns at the start of each constraint
        // Split on: number followed by ≤/<>= (with space), or newlines
        // This handles cases where constraints are separated by spaces
        const items = normalizedText
          .split(/(?=\d+\s+[≤<>=])|\n|•|→/g)
          .map(s => s.trim())
          .filter(s => s.length > 0 && !/^constraints?:?$/i.test(s));
        
        items.forEach(item => {
          // Further split if item contains multiple constraints separated by spaces
          // Look for pattern: ends with number/exponent, followed by space, then starts with number and operator
          const subItems = item.split(/(?<=\^?\d+)\s+(?=\d+\s+[≤<>=])/g);
          subItems.forEach(subItem => {
            const trimmed = subItem.trim();
            if (trimmed.length > 0) {
              constraints.push(trimmed);
            }
          });
        });
      }
    }

    // Method 2: Look for heading with "Constraints" text in HTML
    if (constraints.length === 0) {
      const allElements = Array.from(tempDiv.querySelectorAll('*'));
      constraintsHeading = allElements.find(
        el => {
          const text = el.textContent?.trim() || '';
          return /^constraints?:?$/i.test(text) && ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'STRONG', 'B', 'P'].includes(el.tagName);
        }
      ) || null;
      
      if (constraintsHeading) {
        // Find the next sibling list or paragraph
        let nextElement = constraintsHeading.nextElementSibling;
        while (nextElement) {
          if (nextElement.tagName === 'UL' || nextElement.tagName === 'OL') {
            const items = nextElement.querySelectorAll('li');
            items.forEach(item => {
              const text = item.textContent?.trim();
              if (text && text.length > 0) {
                constraints.push(normalizeConstraintText(text));
              }
            });
            break;
          } else if (nextElement.tagName === 'P' || nextElement.tagName === 'DIV') {
            const text = nextElement.textContent?.trim();
            if (text && text.length > 0) {
              // Split by newlines, bullets, or arrows
              const items = text.split(/\n|•|→/).map(s => s.trim()).filter(s => s.length > 0);
              items.forEach(item => {
                constraints.push(normalizeConstraintText(item));
              });
              if (constraints.length > 0) break;
            }
          }
          nextElement = nextElement.nextElementSibling;
        }
      }
    }

    // Method 3: Look for lists that contain constraint-like patterns
    if (constraints.length === 0) {
      const allLists = tempDiv.querySelectorAll('ul, ol');
      for (const list of Array.from(allLists)) {
        const listText = list.textContent || '';
        // Check if list items look like constraints (contain numbers, ranges, operators)
        if (/≤|>=|<=|>=|\d+\s*≤|\d+\s*>=|\d+\s*<=|\d+\s*>=|^\d+.*≤|^\d+.*>=/i.test(listText)) {
          const items = list.querySelectorAll('li');
          items.forEach(item => {
            const text = item.textContent?.trim();
            if (text && text.length > 0) {
              constraints.push(normalizeConstraintText(text));
            }
          });
          if (constraints.length > 0) break;
        }
      }
    }

    // Get description - remove constraints section if found
    let description = tempDiv.innerHTML;
    if (constraintSectionMatch) {
      // Remove the constraints section from description
      const constraintSection = constraintSectionMatch[0];
      description = description.replace(new RegExp(constraintSection.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), '');
    } else if (constraintsHeading) {
      // Remove the constraints heading and its content
      const constraintsSection = constraintsHeading.parentElement || constraintsHeading;
      if (constraintsSection && constraintsSection !== tempDiv) {
        description = description.replace(constraintsSection.outerHTML, '');
      } else {
        description = description.replace(constraintsHeading.outerHTML, '');
      }
    }

    // Clean up description
    description = description.trim();
    if (!description || description.length < 10) {
      description = questionText;
    }

    // Fallback title
    if (!title) {
      title = 'Coding Problem';
    }

    // Clean up constraints - remove duplicates and empty strings, normalize
    const cleanedConstraints = Array.from(new Set(
      constraints
        .filter(c => c.length > 0)
        .map(c => normalizeConstraintText(c))
    ));

    return { title, description, constraints: cleanedConstraints };
  }, [normalizeConstraintText]);

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

  // Sync timer from backend on mount and update localStorage
  useEffect(() => {
    const syncTimer = async () => {
      const candidateId = user?.candidateId;
      if (!candidateId) return;

      // CRITICAL: Only allow timer sync if timer_started flag is set (i.e., user clicked "Start Assessment")
      const timerStarted = localStorage.getItem('timer_started') === 'true';
      if (!timerStarted) {
        console.log('[CodingContext] Timer not started yet - skipping timer sync. User must click "Start Assessment" first.');
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
      console.log('[CodingContext] Timer not started yet - skipping localStorage timer check. User must click "Start Assessment" first.');
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
          // Parse question text to extract title, description, and constraints
          const parsedQuestion = parseQuestionText(q.question);
          const boilerplate = parseBoilerplateCode(q.boilerplate_code);
          
          return {
            id: index + 1, // Frontend ID
            question_uuid: q.question_uuid, // Backend UUID for API calls
            title: parsedQuestion.title || `Coding Problem ${index + 1}`, // Use parsed title or fallback
            difficulty: 'Medium' as const, // Backend doesn't provide difficulty
            description: parsedQuestion.description || q.question, // Use parsed description or fallback
            examples: q.sample_test_cases.slice(0, 2).map(tc => ({
              input: tc.input,
              output: tc.expected_output,
            })),
            constraints: parsedQuestion.constraints, // Use parsed constraints
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
  }, [user?.candidateId, parseBoilerplateCode, parseQuestionText, normalizeConstraintText]);

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

      const result = await runCodeViaBackend(request, user.candidateId);

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
    setIsSubmitting(true);
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
    submitCodingAnswer(request, user.candidateId)
      .then((result) => {
        setIsSubmitting(false);
        setOutput(
          `Submitted! Score: ${result.score} | ` +
          `Passed: ${result.test_cases_passed}/${result.total_test_cases} ` +
          `(Sample: ${result.sample_test_cases_passed}, Hidden: ${result.hidden_test_cases_passed})`
        );
        console.log('Submission successful:', result);
      })
      .catch((error) => {
        setIsSubmitting(false);
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

