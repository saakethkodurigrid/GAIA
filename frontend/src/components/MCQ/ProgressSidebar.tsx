import { useMCQ } from '../../context/MCQContext';
import { QUESTION_STATUS } from '../../utils/constants';
import QuestionStatusCounters from './QuestionStatusCounters';

const ProgressSidebar = () => {
  const { questions, currentQuestionIndex, questionStatuses, goToQuestion } = useMCQ();

  const getQuestionButtonClass = (index: number, questionId: number): string => {
    const status = questionStatuses[questionId] || QUESTION_STATUS.NOT_ANSWERED;
    const isActive = index === currentQuestionIndex;
    
    let className = 'aspect-square rounded-lg border-2 font-semibold text-sm cursor-pointer flex items-center justify-center relative transition-all hover:scale-105';
    
    if (isActive) {
      // Active question gets brown border
      className += ' border-amber-700 border-[3px]';
    }
    
    if (status === QUESTION_STATUS.ANSWERED) {
      if (isActive) {
        className += ' bg-green-100 text-green-600';
      } else {
        className += ' bg-green-100 border-green-500 text-green-600';
      }
    } else if (status === QUESTION_STATUS.MARKED) {
      if (isActive) {
        className += ' bg-purple-600 text-white';
      } else {
        className += ' bg-purple-600 border-purple-600 text-white';
      }
    } else {
      if (isActive) {
        className += ' bg-yellow-100 text-gray-800';
      } else {
        className += ' bg-yellow-100 border-yellow-400 text-gray-800';
      }
    }
    
    return className;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <h3 className="text-base font-semibold text-gray-800 mb-1">Question Overview</h3>
        <QuestionStatusCounters />
      </div>
      
      <div className="flex flex-col gap-3">
        <h3 className="text-base font-semibold text-gray-800 mb-1">All Questions</h3>
        <div className="grid grid-cols-4 gap-2">
          {questions.map((question, index) => (
            <button
              key={question.id}
              className={getQuestionButtonClass(index, question.id)}
              onClick={() => goToQuestion(index)}
            >
              <span className="text-sm">{index + 1}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProgressSidebar;
