import { useState, useRef, useEffect } from 'react';
import { useSystemDesign } from '../../context/SystemDesignContext';

const ClarifyingChat = () => {
  const { chatMessages, sendMessage } = useSystemDesign();
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Helper function to parse markdown bold syntax (**text**) and render as bold
  const parseMarkdownBold = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        const boldText = part.slice(2, -2);
        return <strong key={index}>{boldText}</strong>;
      }
      return part;
    });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // Debug: Log chat messages updates
  useEffect(() => {
    console.log('[Chat] 📝 Chat messages updated. Count:', chatMessages.length);
    console.log('[Chat] 📝 Messages:', chatMessages.map(m => ({
      id: m.id,
      role: m.role,
      content: m.content.substring(0, 50) + (m.content.length > 50 ? '...' : '')
    })));
  }, [chatMessages]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [inputMessage]);

  const handleSend = async () => {
    if (!inputMessage.trim() || isSending) return;

    const message = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);

    await sendMessage(message);
    setIsSending(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-200 bg-white">
        <h3 className="text-lg font-semibold text-gray-800 mb-1">Ask Clarifying Questions</h3>
        <p className="text-sm text-gray-600 m-0">Get help understanding the requirements</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {chatMessages.length === 0 ? (
          <div className="text-center text-gray-500 mt-10">
            <p className="text-sm mb-2">Start by asking clarifying questions about the system design problem.</p>
            <p className="text-xs text-gray-400 italic">The assistant will help you understand the requirements without giving complete solutions.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {chatMessages.map((message) => (
              <div
                key={message.id}
                className="mb-4 animate-fadeIn"
              >
                <div className={`text-xs font-semibold mb-1 ${
                  message.role === 'user' ? 'text-blue-600' : 'text-gray-600'
                }`}>
                  {message.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div
                  className={`rounded-lg px-3 py-2 text-sm ${
                    message.role === 'user'
                      ? 'bg-blue-50 text-blue-900 border border-blue-200'
                      : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
                  }`}
                >
                  <p className="whitespace-pre-wrap m-0 leading-relaxed">{parseMarkdownBold(message.content)}</p>
                </div>
              </div>
            ))}
            {isSending && (
              <div className="mb-4">
                <div className="text-xs font-semibold mb-1 text-gray-600">Assistant</div>
                <div className="bg-white border border-gray-200 rounded-lg px-3 py-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></span>
                    <span className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                    <span className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form 
        className="px-4 py-4 border-t border-gray-200 bg-white flex gap-2.5 items-end"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <textarea
          ref={textareaRef}
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Ask a question..."
          disabled={isSending}
          rows={1}
          className="flex-1 px-3 py-3 border border-gray-200 rounded-md text-sm focus:outline-none focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed resize-none overflow-y-auto min-h-[44px] max-h-[150px]"
          style={{ height: 'auto' }}
        />
        <button
          type="submit"
          disabled={!inputMessage.trim() || isSending}
          className="px-6 py-3 bg-blue-600 text-white rounded-md text-sm font-semibold hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed self-end"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ClarifyingChat;

