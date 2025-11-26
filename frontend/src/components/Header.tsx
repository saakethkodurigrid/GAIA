import { useState, useRef, useEffect } from 'react';
import gdLogo from '../assets/gd-logo.svg';

interface HeaderProps {
  showUserInfo?: boolean;
  showLogout?: boolean;
  showTechInterviewLogo?: boolean;
  showTimer?: boolean;
  timerValue?: string;
  transparent?: boolean;
  user?: {
    name?: string;
    email?: string;
  } | null;
  onLogout?: () => void;
}

const Header = ({ showUserInfo = false, showLogout = false, showTechInterviewLogo = false, showTimer = false, timerValue = '60:00', transparent = false, user, onLogout }: HeaderProps) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    }
    setIsDropdownOpen(false);
  };

  return (
    <header className={transparent ? "bg-transparent" : "bg-white shadow-md"}>
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            {showTechInterviewLogo && (
              <div className="flex items-center gap-2">
                <div className="text-2xl font-bold text-yellow-500">&lt;/&gt;</div>
                <span className="text-xl font-semibold text-gray-900">TechInterview</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 pr-4">
            {showUserInfo && user && (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                  type="button"
                >
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-600 font-semibold">
                      {(user.name || user.email || 'U').charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <svg 
                    className={`w-4 h-4 text-gray-500 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {isDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                    <div className="px-4 py-2 border-b border-gray-200">
                      <p className="text-sm font-medium text-gray-900">{user.name || 'User'}</p>
                      <p className="text-xs text-gray-500 truncate">{user.email}</p>
                    </div>
                    {showLogout && (
                      <button
                        onClick={handleLogout}
                        type="button"
                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        <span>Logout</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
            {/* Timer */}
            {showTimer && (
              <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg shadow-sm">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-semibold text-gray-900">{timerValue}</span>
              </div>
            )}
            {/* Logo on the right */}
            <img src={gdLogo} alt="Grid Dynamics" className="h-8" />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
