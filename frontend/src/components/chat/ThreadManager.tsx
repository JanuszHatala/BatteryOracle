import React, { useState } from 'react';
import { Thread } from '../../types/api';
import { Button } from '../ui/Button';
import { Plus, Edit2, Check, X, Trash2, Download, MessageSquare } from 'lucide-react';

interface ThreadManagerProps {
  threads: Thread[];
  activeThreadId: number | null;
  onSelectThread: (threadId: number) => void;
  onCreateThread: () => void;
  onRenameThread: (threadId: number, newTitle: string) => void;
  onDeleteThread: (threadId: number) => void;
  onClearThread: (threadId: number) => void;
  onExportThread: (threadId: number) => void;
}

export const ThreadManager: React.FC<ThreadManagerProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onRenameThread,
  onDeleteThread,
  onClearThread,
  onExportThread
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');

  const activeThread = threads.find((t) => t.id === activeThreadId);

  const startRename = () => {
    if (!activeThread) return;
    setEditTitle(activeThread.title);
    setIsEditing(true);
  };

  const saveRename = () => {
    if (activeThread && editTitle.trim()) {
      onRenameThread(activeThread.id, editTitle.trim());
    }
    setIsEditing(false);
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 sm:p-3 bg-slate-900 border-b border-slate-800 text-xs">
      <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-1">
        <MessageSquare className="w-4 h-4 text-indigo-400 shrink-0" />

        {isEditing ? (
          <div className="flex items-center gap-1 flex-1 min-w-0 max-w-xs">
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveRename();
                if (e.key === 'Escape') setIsEditing(false);
              }}
              autoFocus
              className="bg-slate-950 border border-indigo-500 rounded px-2 py-1 text-xs text-slate-100 w-full min-w-0 focus:outline-none"
            />
            <button
              onClick={saveRename}
              className="text-emerald-400 hover:text-emerald-300 p-1 shrink-0"
              title="Save Title"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="text-slate-400 hover:text-slate-300 p-1 shrink-0"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1 min-w-0 flex-1 max-w-[220px]">
            <select
              value={activeThreadId || ''}
              onChange={(e) => onSelectThread(Number(e.target.value))}
              className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-full min-w-0 truncate"
            >
              {threads.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title} ({t.message_count} msgs)
                </option>
              ))}
            </select>
            {activeThread && (
              <button
                onClick={startRename}
                className="text-slate-400 hover:text-slate-200 p-1 shrink-0"
                title="Rename Thread"
              >
                <Edit2 className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        <Button
          variant="secondary"
          size="sm"
          onClick={onCreateThread}
          className="h-7 text-xs px-2 whitespace-nowrap shrink-0"
          title="Create New Thread"
        >
          <Plus className="w-3.5 h-3.5 mr-1 shrink-0" />
          <span>New Thread</span>
        </Button>
      </div>

      {activeThread && (
        <div className="flex items-center gap-1 sm:gap-1.5 shrink-0 ml-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onExportThread(activeThread.id)}
            className="h-7 text-xs text-slate-400 hover:text-slate-200 px-2 whitespace-nowrap shrink-0"
            title="Export Thread Markdown"
          >
            <Download className="w-3.5 h-3.5 mr-1 shrink-0" />
            <span>Export</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => onClearThread(activeThread.id)}
            className="h-7 text-xs text-amber-400 hover:text-amber-300 px-2 whitespace-nowrap shrink-0"
            title="Clear Messages"
          >
            Clear
          </Button>

          {threads.length > 1 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDeleteThread(activeThread.id)}
              className="h-7 text-xs text-rose-400 hover:text-rose-300 px-1.5 shrink-0"
              title="Delete Thread"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
