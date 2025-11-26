import { useState, useRef, useEffect } from 'react';
import { useCoding } from '../../context/CodingContext';
import { useCodingSession } from '../../hooks/useCodingSession';

interface LanguageTabsProps {
  onSubmitSection?: () => void;
}

const LanguageTabs = ({ onSubmitSection }: LanguageTabsProps) => {
  const { selectedLanguage, setLanguage, resetCode } = useCoding();
  const { currentProblemIndex, totalProblems } = useCodingSession();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const languages = [
    { id: 'python', label: 'Python' },
    { id: 'javascript', label: 'JavaScript' },
    { id: 'java', label: 'Java' }
  ] as const;

  const currentLanguage = languages.find(lang => lang.id === selectedLanguage) || languages[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
      {/* Left side - Language Dropdown and Reset */}
      <div className="flex items-center gap-3">
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="px-4 py-2 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 flex items-center gap-2 hover:bg-gray-50"
          >
            <span>{currentLanguage.label}</span>
            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {isOpen && (
            <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded shadow-lg z-10 min-w-full">
              {languages.map((lang) => (
                <button
                  key={lang.id}
                  onClick={() => {
                    setLanguage(lang.id);
                    setIsOpen(false);
                  }}
                  className={`w-full px-4 py-2 text-left text-sm transition-colors whitespace-nowrap ${
                    selectedLanguage === lang.id
                      ? 'bg-yellow-50 text-gray-900 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          )}
        </div>
        
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

      {/* Right side - Question info and Submit Section */}
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium text-gray-700">
          Question {currentProblemIndex + 1} of {totalProblems}
        </span>
        <button
          onClick={() => onSubmitSection?.()}
          className="px-4 py-2 text-sm font-medium bg-green-600 text-white rounded transition-colors hover:bg-green-700"
        >
          Submit Section
        </button>
      </div>
    </div>
  );
};

export default LanguageTabs;

