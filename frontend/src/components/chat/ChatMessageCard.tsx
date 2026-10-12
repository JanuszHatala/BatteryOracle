import React, { useState } from 'react';
import { Message } from '../../types/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, GitFork, Trash2, User, Bot, Copy, Check } from 'lucide-react';

interface ChatMessageCardProps {
  message: Message;
  onFork: (messageId: number) => void;
  onDelete: (messageId: number) => void;
  onToggleCollapse: (messageId: number) => void;
}

export const ChatMessageCard: React.FC<ChatMessageCardProps> = ({
  message,
  onFork,
  onDelete,
  onToggleCollapse
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const isCollapsed = message.is_collapsed;

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      id={`msg-${message.id}`}
      className={`rounded-xl border transition-all ${
        isUser
          ? 'bg-emerald-950/20 border-emerald-800/40 ml-4'
          : 'bg-indigo-950/20 border-indigo-800/40 mr-4'
      }`}
    >
      {/* Header bar: role indicator, collapse button, actions */}
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-slate-800/60 text-xs">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggleCollapse(message.id)}
            className="text-slate-400 hover:text-slate-200 transition-colors p-0.5 rounded"
            title={isCollapsed ? 'Expand Message' : 'Collapse Message'}
          >
            {isCollapsed ? (
              <ChevronRight className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          <span
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
              isUser
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
            }`}
          >
            {isUser ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
            {isUser ? 'User' : 'Battery Oracle AI'}
          </span>

          {message.created_at && (
            <span className="text-[10px] text-slate-500">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>

        {/* Right-aligned actions: Copy, Fork, Delete */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="text-slate-400 hover:text-slate-200 p-1 rounded transition-colors"
            title="Copy text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={() => onFork(message.id)}
            className="text-slate-400 hover:text-indigo-300 p-1 rounded transition-colors flex items-center gap-1 text-[11px]"
            title="Fork thread from this message"
          >
            <GitFork className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Fork</span>
          </button>

          <button
            onClick={() => onDelete(message.id)}
            className="text-slate-400 hover:text-rose-400 p-1 rounded transition-colors"
            title="Delete message"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Message content */}
      {!isCollapsed && (
        <div className="p-3.5 text-xs text-slate-200 prose prose-invert prose-xs max-w-none leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ ...props }) => <h1 className="text-base font-bold text-slate-100 my-2" {...props} />,
              h2: ({ ...props }) => <h2 className="text-sm font-semibold text-slate-200 my-1.5" {...props} />,
              h3: ({ ...props }) => <h3 className="text-xs font-semibold text-slate-300 my-1" {...props} />,
              ul: ({ ...props }) => <ul className="list-disc pl-4 space-y-1 my-1" {...props} />,
              ol: ({ ...props }) => <ol className="list-decimal pl-4 space-y-1 my-1" {...props} />,
              li: ({ ...props }) => <li className="text-slate-300" {...props} />,
              p: ({ ...props }) => <p className="mb-2 last:mb-0" {...props} />,
              code: ({ ...props }) => (
                <code className="bg-slate-900 border border-slate-800 px-1 py-0.5 rounded text-indigo-300 font-mono text-[11px]" {...props} />
              ),
              pre: ({ ...props }) => (
                <pre className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 overflow-x-auto text-[11px] my-1.5 font-mono" {...props} />
              )
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
};
