import { useState } from 'react';
import { useMCQ } from '../../context/MCQContext';
import { submitAssessment } from '../../api/questions.api';
import { QUESTION_STATUS } from '../../utils/constants';
import type { SubmitSectionModalProps } from '../../types';
import { useAuth } from '../../context/AuthContext';
import ConfirmationModal from '../ConfirmationModal';

const SubmitSectionModal = ({ isOpen, onClose, onSubmit }: SubmitSectionModalProps) => {
  const { answers, savedAnswers, questions, getStatusCounts } = useMCQ();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const counts = getStatusCounts();

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    
    // Use savedAnswers, but also include any currently selected answers that haven't been saved yet
    const finalAnswers = { ...savedAnswers, ...answers };
    
    // Get candidate ID from auth context
    const candidateId = user?.candidateId;
    if (!candidateId) {
      setSubmitError('Candidate ID not found. Please log in again.');
      setIsSubmitting(false);
      return;
    }

    // Navigate immediately - don't wait for API call
    onSubmit(finalAnswers);
    
    // Submit to backend in the background (fire and forget)
    submitAssessment(finalAnswers, questions, candidateId)
      .then((response) => {
        if (!response.success) {
          console.error('Background submission failed:', response.message);
        } else {
          console.log('Background submission successful');
        }
      })
      .catch((error) => {
        console.error('Error submitting assessment in background:', error);
        // Don't show error to user since they've already navigated away
      });
  };

  const answeredCount = counts[QUESTION_STATUS.ANSWERED] || 0;
  const markedCount = counts[QUESTION_STATUS.MARKED] || 0;
  const totalQuestions = questions.length;
  const notAnsweredCount = totalQuestions - answeredCount;

  const customContent = (
    <>
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

      {/* Error message */}
      {submitError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {submitError}
        </div>
      )}

      <p className="text-gray-700 mb-4">Do you want to continue with the submission?</p>
    </>
  );

  return (
    <ConfirmationModal
      isOpen={isOpen}
      onClose={onClose}
      onConfirm={handleSubmit}
      title="Submit Section"
      customContent={customContent}
      confirmButtonText="Submit"
      confirmButtonColor="yellow"
      isSubmitting={isSubmitting}
    />
  );
};

export default SubmitSectionModal;
