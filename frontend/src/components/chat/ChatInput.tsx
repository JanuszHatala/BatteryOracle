import React, { useRef, useEffect } from 'react';
import { Send, CornerDownLeft } from 'lucide-react';
import { Button } from '../ui/Button';

interface ChatInputProps {
  value: string;
  onChange: (val: string) => void;
  onSend: () => void;
  isLoading: boolean;
  enterMode: 'newline' | 'send';
  onToggleEnterMode: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  isLoading,
  enterMode,
  onToggleEnterMode
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea up to 35% viewport height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const maxHeight = window.innerHeight * 0.35;
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (enterMode === 'send') {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (value.trim() && !isLoading) onSend();
      }
    } else {
      // 'newline' mode: Ctrl+Enter or Cmd+Enter to send
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (value.trim() && !isLoading) onSend();
      }
    }
  };

  return (
    <div className="p-3 bg-slate-900 border-t border-slate-800">
      <div className="relative bg-slate-950 border border-slate-700/80 rounded-xl focus-within:border-indigo-500 transition-colors shadow-inner">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask AI about wakelocks, subsystem drain, power rails, or background anomalies..."
          rows={2}
          className="w-full bg-transparent p-3 pr-12 text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none font-sans"
        />

        <div className="absolute right-2.5 bottom-2.5">
          <Button
            variant="primary"
            size="sm"
            onClick={onSend}
            disabled={!value.trim() || isLoading}
            className="w-8 h-8 p-0 rounded-lg flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between mt-2 px-1 text-[11px] text-slate-400">
        <button
          onClick={onToggleEnterMode}
          className="hover:text-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
        >
          <CornerDownLeft className="w-3 h-3 text-slate-500" />
          <span>
            {enterMode === 'send'
              ? 'Enter: Send • Shift+Enter: New Line'
              : 'Enter: New Line • Ctrl+Enter: Send'}
          </span>
        </button>

        <span className="text-slate-400">Markdown supported</span>
      </div>
    </div>
  );
};
