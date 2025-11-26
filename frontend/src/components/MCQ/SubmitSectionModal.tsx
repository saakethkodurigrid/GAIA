import { useState } from 'react';
import { useMCQ } from '../../context/MCQContext';
import { submitAssessment } from '../../api/questions.api';
import { QUESTION_STATUS } from '../../utils/constants';
import type { SubmitSectionModalProps } from '../../types';

const SubmitSectionModal = ({ isOpen, onClose, onSubmit }: SubmitSectionModalProps) => {
  const { answers, savedAnswers, questions, getStatusCounts } = useMCQ();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const counts = getStatusCounts();

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // Use savedAnswers, but also include any currently selected answers that haven't been saved yet
      const finalAnswers = { ...savedAnswers, ...answers };
      await submitAssessment(finalAnswers);
      onSubmit(finalAnswers);
    } catch (error) {
      console.error('Error submitting assessment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const answeredCount = counts[QUESTION_STATUS.ANSWERED] || 0;
  const markedCount = counts[QUESTION_STATUS.MARKED] || 0;
  const totalQuestions = questions.length;
  const notAnsweredCount = totalQuestions - answeredCount;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1000]" 
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-xl p-8 max-w-[500px] w-[90%] shadow-[0_10px_25px_rgba(0,0,0,0.2)]" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with warning icon */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-800">Confirm Submission</h2>
        </div>

        {/* Content */}
        <div className="mb-6">
          <p className="mb-4 text-gray-700">Please review the following before submitting:</p>
          
          {/* Warning list */}
          <ul className="mb-6 space-y-2">
            {notAnsweredCount > 0 && (
              <li className="flex items-center gap-2 text-red-600">
                <span className="text-red-600">•</span>
                <span>{notAnsweredCount} {notAnsweredCount === 1 ? 'question' : 'questions'} not answered</span>
              </li>
            )}
            {markedCount > 0 && (
              <li className="flex items-center gap-2 text-red-600">
                <span className="text-red-600">•</span>
                <span>{markedCount} {markedCount === 1 ? 'question' : 'questions'} marked for review</span>
              </li>
            )}
          </ul>

          <p className="text-gray-700 mb-6">Do you want to continue with the submission?</p>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-4">
          <button 
            className="px-6 py-3 bg-amber-50 border border-amber-200 rounded-lg text-base font-medium cursor-pointer transition-all hover:bg-amber-100 text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed" 
            onClick={onClose} 
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            className="px-6 py-3 bg-yellow-400 text-gray-900 rounded-lg text-base font-medium cursor-pointer transition-colors hover:bg-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Anyway'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubmitSectionModal;
