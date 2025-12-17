import { useState, useRef, useEffect } from 'react';

const Footer = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close modal when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsModalOpen(false);
      }
    };

    if (isModalOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isModalOpen]);

  return (
    <footer className="w-full bg-white border-t border-gray-200 py-4">
      <div className="w-full px-6">
        <div className="flex justify-between items-center">
          <div className="relative">
            <button
              ref={buttonRef}
              onClick={() => setIsModalOpen(!isModalOpen)}
              className="text-sm font-bold hover:opacity-80 transition-opacity"
              style={{ color: '#155DFC' }}
            >
              Contact Support
            </button>
            {isModalOpen && (
              <div
                ref={modalRef}
                className="absolute bottom-full left-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 min-w-[120px]"
              >
                <p className="text-sm text-gray-700">email</p>
              </div>
            )}
          </div>
          <p className="text-gray-400 text-sm">
            Grid Dynamics © 2006-2025
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

