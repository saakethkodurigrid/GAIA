import type { TourStep } from '../../context/TourContext';

export const mcqTourSteps: TourStep[] = [
  {
    target: '[data-tour="header"]',
    title: 'Welcome to multiple choice questions assessment!',
    content: 'This short tour will help you understand how to navigate and answer the MCQ questions. Click Next to begin the quick tour.',
    placement: 'center'
  },
  {
    target: '[data-tour="sidebar"]',
    title: 'Question Panel',
    content: 'This is your question navigator. You can jump to any question from here.',
    placement: 'right'
  },
  {
    target: '[data-tour="question-text"]',
    title: 'Question Text',
    content: 'The question appears here. Read carefully before choosing an option.',
    placement: 'center'
  },
  {
    target: '[data-tour="options"]',
    title: 'Options',
    content: 'Select one of the choices below. You can change your option at any time.',
    placement: 'left-side'
  },
  {
    target: '[data-tour="mark-for-review"]',
    title: 'Mark for Review',
    content: 'Use this to revisit questions later. Marked questions will appear with a flag.',
    placement: 'bottom'
  },
  {
    target: '[data-tour="save-next"]',
    title: 'Save & Next Button',
    content: 'Click Save after selecting your answer. Unsaved answers won\'t be counted.',
    placement: 'center'
  },
  {
    target: '[data-tour="timer"]',
    title: 'Timer',
    content: 'This timer shows the total time remaining. Your test auto-submits when time ends.',
    placement: 'center'
  },
  {
    target: '[data-tour="submit-button"]',
    title: 'Submit Section',
    content: 'Once you have submitted answers for all the questions, click Submit Section. Your answers will be evaluated and locked for this section.',
    placement: 'center'
  }
];

export const codingTourSteps: TourStep[] = [
  {
    target: '[data-tour="header"]',
    title: 'Welcome to your coding assessment!',
    content: 'You\'ll solve a set of programming questions here. Each question includes a description, examples, and test cases to help you verify your solution. Click Next to begin the quick tour.',
    placement: 'center'
  },
  {
    target: '[data-tour="question-nav"]',
    title: 'Your Question Navigator',
    content: 'Use this panel to switch between questions anytime. Finished questions will show a progress indicator so you know what\'s done.',
    placement: 'right'
  },
  {
    target: '[data-tour="problem-description"]',
    title: 'Problem Title and Description',
    content: 'Each problem starts with its title. And you will find the full description of the task. Read this part carefully — most important details and constraints are explained here.',
    placement: 'center'
  },
  {
    target: '[data-tour="problem-description"]',
    title: 'Examples',
    content: 'These examples show valid inputs and expected outputs. They\'re designed to help you understand sample test cases and the expected logic.',
    placement: 'center'
  },
  {
    target: '[data-tour="language-selector"]',
    title: 'Choose Your Language',
    content: 'You can write your solution in the language you are most comfortable with. Choose from Python, JavaScript, or Java.',
    placement: 'center'
  },
  {
    target: '[data-tour="code-editor"]',
    title: 'Code Editor',
    content: 'Write your solution here. The editor supports indentation, syntax highlighting, and resets if you want to start over.',
    placement: 'center'
  },
  {
    target: '[data-tour="test-cases"]',
    title: 'Run & Test Your Code',
    content: 'Use Run Code to test with selected inputs. Use Run All Test cases to verify your solution against all provided cases before submitting. Once you\'re confident your code works, click Submit Solution.',
    placement: 'center'
  },
  {
    target: '[data-tour="submit-solution"]',
    title: 'Submit Section',
    content: 'Once you have submitted answers for all the questions, click Submit Section. Your answers will be evaluated and locked for this section.',
    placement: 'center'
  }
];

export const systemDesignTourSteps: TourStep[] = [
  {
    target: '[data-tour="header"]',
    title: 'Welcome to System Design Assessment',
    content: 'This is the header section. You can see the timer and submit button here.',
    placement: 'bottom'
  },
  {
    target: '[data-tour="problem-description"]',
    title: 'Problem Description',
    content: 'Read the system design problem and requirements here.',
    placement: 'bottom'
  },
  {
    target: '[data-tour="canvas"]',
    title: 'Design Canvas',
    content: 'Use this Excalidraw canvas to create your system architecture diagram. Draw components, connections, and annotations.',
    placement: 'bottom'
  },
  {
    target: '[data-tour="chat"]',
    title: 'Clarifying Questions',
    content: 'Ask clarifying questions about the requirements using this chat interface.',
    placement: 'left'
  },
  {
    target: '[data-tour="submit-button"]',
    title: 'System Design Tutorial Complete!',
    content: 'Perfect! You\'ve completed all tutorials. Are you ready to start the test? Click "Start Test" when you\'re ready!',
    placement: 'center'
  }
];

