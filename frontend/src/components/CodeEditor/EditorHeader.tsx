import { useCoding } from '../../context/CodingContext';

const EditorHeader = () => {
  const { resetCode } = useCoding();

  return (
    <div className="flex items-center justify-end px-4 py-3 bg-white border-b border-gray-200">
      <button
        onClick={resetCode}
        className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Reset
      </button>
    </div>
  );
};

export default EditorHeader;

