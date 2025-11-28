import Timer from './Timer';

interface DesignHeaderProps {
  onSubmit: () => void;
}

const DesignHeader = ({ onSubmit }: DesignHeaderProps) => {
  return (
    <header className="w-full max-w-full flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200 shadow-sm m-0 flex-shrink-0">
      <button className="flex items-center gap-2 px-4 py-2 bg-transparent border-none cursor-pointer text-base text-gray-800 hover:text-blue-600 transition-colors">
        <span className="text-xl">←</span>
        Back
      </button>
      <div className="flex items-center gap-3 flex-1 justify-center">
        <span className="text-2xl text-gray-600">&lt;/&gt;</span>
        <h1 className="text-2xl font-semibold text-gray-800">System Design Assessment</h1>
        <span className="w-2 h-2 rounded-full bg-red-500"></span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-md font-semibold text-base">
          <span className="text-base">🕐</span>
          <Timer />
        </div>
        <button 
          onClick={onSubmit}
          className="px-6 py-2 bg-yellow-400 text-gray-800 rounded-md font-semibold text-base cursor-pointer hover:bg-yellow-500 transition-colors"
        >
          Submit Solution
        </button>
      </div>
    </header>
  );
};

export default DesignHeader;

