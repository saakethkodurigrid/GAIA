import { useMCQ } from '../../context/MCQContext';
import OptionsList from './OptionsList';
import { useMCQNavigation } from '../../hooks/useMCQNavigation';

interface QuestionCardProps {
  onShowSubmitModal: () => void;
}

const QuestionCard = ({ onShowSubmitModal }: QuestionCardProps) => {
  const { currentQuestion, markForReview, clearSelection, hasUnsavedChanges, saveAndNext, goToNextOnly, currentQuestionIndex, questions } = useMCQ();
  const { goToPrevious, canGoPrevious } = useMCQNavigation();

  if (!currentQuestion) return null;

  const handleMarkForReview = () => {
    markForReview(currentQuestion.id);
  };

  const handleClearSelection = () => {
    clearSelection(currentQuestion.id);
  };


  return (
    <div className="w-full max-w-full flex flex-col gap-5">
      <div className="flex justify-between items-center w-full">
        <span className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
          {currentQuestion.topic}
        </span>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600 font-medium">
            Question {currentQuestionIndex + 1} of {questions.length}
          </span>
          <button
            onClick={onShowSubmitModal}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition-colors"
          >
            Submit Section
          </button>
        </div>
      </div>
      
      <div className="text-xl font-semibold text-gray-800 leading-relaxed my-3 w-full break-words">
        {currentQuestion.question}
      </div>
      
      <OptionsList />
      
      <div className="flex justify-between items-center gap-4 mt-5 w-full">
        <div className="flex items-center gap-4">
          <button 
            className="flex items-center gap-2 px-5 py-2 bg-transparent border-2 border-gray-200 rounded-lg text-sm font-medium cursor-pointer transition-all hover:border-gray-400 hover:bg-gray-50 text-gray-800" 
            onClick={handleMarkForReview}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
            </svg>
            Mark for Review
          </button>
          
          <button 
            className="flex items-center gap-2 px-5 py-2 bg-transparent border-2 border-gray-200 rounded-lg text-sm font-medium cursor-pointer transition-all hover:border-gray-400 hover:bg-gray-50 text-gray-800" 
            onClick={handleClearSelection}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear Selection
          </button>
        </div>
        
        <div className="flex items-center gap-4">
          <button
            className={`px-6 py-2 rounded-lg text-sm font-medium cursor-pointer transition-all ${
              !canGoPrevious 
                ? 'bg-gray-100 border-2 border-gray-200 text-gray-400 opacity-50 cursor-not-allowed' 
                : 'bg-gray-100 border-2 border-gray-200 text-gray-600 hover:bg-gray-200 hover:border-gray-300'
            }`}
            onClick={goToPrevious}
            disabled={!canGoPrevious}
          >
            Previous
          </button>
          
          {hasUnsavedChanges() ? (
            <button 
              className="px-6 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold cursor-pointer transition-colors hover:bg-gray-800" 
              onClick={saveAndNext}
            >
              Save & Next
            </button>
          ) : (
            <button 
              className="px-6 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold cursor-pointer transition-colors hover:bg-gray-800" 
              onClick={goToNextOnly}
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuestionCard;
