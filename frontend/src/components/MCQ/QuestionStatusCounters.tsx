import { useMCQ } from '../../context/MCQContext';
import { QUESTION_STATUS } from '../../utils/constants';

const QuestionStatusCounters = () => {
  const { getStatusCounts } = useMCQ();
  const counts = getStatusCounts();

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3 p-2">
        <div className="w-6 h-6 rounded bg-green-100 border-2 border-green-500"></div>
        <span className="flex-1 text-sm text-gray-600">Answered</span>
        <span className="font-semibold text-gray-800 min-w-6 text-right">{counts[QUESTION_STATUS.ANSWERED] || 0}</span>
      </div>
      <div className="flex items-center gap-3 p-2">
        <div className="w-6 h-6 rounded bg-purple-600 border-2 border-purple-600"></div>
        <span className="flex-1 text-sm text-gray-600">Mark for Review</span>
        <span className="font-semibold text-gray-800 min-w-6 text-right">{counts[QUESTION_STATUS.MARKED] || 0}</span>
      </div>
      <div className="flex items-center gap-3 p-2">
        <div className="w-6 h-6 rounded bg-yellow-100 border-2 border-yellow-400"></div>
        <span className="flex-1 text-sm text-gray-600">Not Answered</span>
        <span className="font-semibold text-gray-800 min-w-6 text-right">{counts[QUESTION_STATUS.NOT_ANSWERED] || 0}</span>
      </div>
    </div>
  );
};

export default QuestionStatusCounters;
