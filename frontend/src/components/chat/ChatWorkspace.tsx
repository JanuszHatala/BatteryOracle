import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Thread, Message } from '../../types/api';
import { api } from '../../api/client';
import { ThreadManager } from './ThreadManager';
import { ChatMessageCard } from './ChatMessageCard';
import { ChatInput } from './ChatInput';
import { useDialog } from '../ui/DialogContext';
import { Loader2 } from 'lucide-react';

interface ChatWorkspaceProps {
  reportId: number;
  enterMode?: 'newline' | 'send';
  onChangeEnterMode?: (mode: 'newline' | 'send') => void;
  activeScope?: string;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  reportId,
  enterMode: propEnterMode,
  onChangeEnterMode,
  activeScope
}) => {
  const { showError, confirm } = useDialog();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [localEnterMode, setLocalEnterMode] = useState<'newline' | 'send'>(propEnterMode || 'newline');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Sync enterMode when prop changes or fetch from settings if not provided
  useEffect(() => {
    if (propEnterMode) {
      setLocalEnterMode(propEnterMode);
    } else {
      api.getSettings()
        .then((s) => {
          if (s.chat_enter_mode === 'newline' || s.chat_enter_mode === 'send') {
            setLocalEnterMode(s.chat_enter_mode);
          }
        })
        .catch(() => {});
    }
  }, [propEnterMode]);

  const effectiveEnterMode = propEnterMode || localEnterMode;

  const handleToggleEnterMode = async () => {
    const nextMode: 'newline' | 'send' = effectiveEnterMode === 'send' ? 'newline' : 'send';
    setLocalEnterMode(nextMode);
    if (onChangeEnterMode) {
      onChangeEnterMode(nextMode);
    }
    try {
      await api.updateSettings({ chat_enter_mode: nextMode });
    } catch (err) {
      console.error('Failed to persist chat_enter_mode:', err);
    }
  };

  // Load threads for report
  const loadThreads = useCallback(async () => {
    try {
      const data = await api.getThreads(reportId);
      setThreads(data);
      if (data.length > 0) {
        if (!activeThreadId || !data.some((t) => t.id === activeThreadId)) {
          setActiveThreadId(data[0].id);
        }
      } else {
        // Create initial thread
        const newThread = await api.createThread(reportId, 'Initial Investigation');
        setThreads([newThread]);
        setActiveThreadId(newThread.id);
      }
    } catch (err) {
      console.error('Failed to load threads:', err);
    }
  }, [reportId, activeThreadId]);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  // Load messages when activeThreadId changes
  const loadMessages = useCallback(async (threadId: number) => {
    setIsLoadingMessages(true);
    try {
      const msgs = await api.getThreadMessages(threadId);
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load messages:', err);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    if (activeThreadId) {
      loadMessages(activeThreadId);
    } else {
      setMessages([]);
    }
  }, [activeThreadId, loadMessages]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const handleSendMessage = async () => {
    if (!activeThreadId || !inputValue.trim() || isSending) return;
    const prompt = inputValue.trim();
    setInputValue('');
    setIsSending(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await api.sendMessage(activeThreadId, prompt, activeScope || undefined, controller.signal);
      await loadMessages(activeThreadId);
      await loadThreads();
    } catch (err: any) {
      if (err.name === 'AbortError' || err.message?.includes('aborted')) {
        console.log('Chat message generation cancelled by user.');
        return;
      }
      console.error('Failed to send message:', err);
      // Restore user input so they don't lose their message on error
      setInputValue(prompt);
      showError(err, 'Sending Chat Message to Oracle AI');
    } finally {
      setIsSending(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancelSending = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsSending(false);
    }
  };

  const handleCreateThread = async () => {
    try {
      const newThread = await api.createThread(reportId, `Investigation ${threads.length + 1}`);
      setThreads((prev) => [...prev, newThread]);
      setActiveThreadId(newThread.id);
    } catch (err) {
      console.error('Failed to create thread:', err);
      showError(err, 'Creating Investigation Thread');
    }
  };

  const handleRenameThread = async (threadId: number, newTitle: string) => {
    try {
      const updated = await api.renameThread(threadId, newTitle);
      setThreads((prev) => prev.map((t) => (t.id === threadId ? updated : t)));
    } catch (err) {
      console.error('Failed to rename thread:', err);
      showError(err, 'Renaming Investigation Thread');
    }
  };

  const handleDeleteThread = async (threadId: number) => {
    const target = threads.find((t) => t.id === threadId);
    const ok = await confirm({
      title: 'Delete Conversation Thread',
      message: `Are you sure you want to permanently delete "${target?.title || 'this thread'}" and all its messages?`,
      confirmLabel: 'Delete Thread',
      variant: 'danger'
    });
    if (!ok) return;

    try {
      await api.deleteThread(threadId);
      const remaining = threads.filter((t) => t.id !== threadId);
      setThreads(remaining);
      setActiveThreadId(remaining.length > 0 ? remaining[0].id : null);
    } catch (err) {
      console.error('Failed to delete thread:', err);
      showError(err, 'Deleting Thread');
    }
  };

  const handleClearThread = async (threadId: number) => {
    const ok = await confirm({
      title: 'Clear Thread History',
      message: 'Clear all messages in this investigation thread? This action cannot be undone.',
      confirmLabel: 'Clear Messages',
      variant: 'warning'
    });
    if (!ok) return;

    try {
      await api.clearThread(threadId);
      setMessages([]);
      await loadThreads();
    } catch (err) {
      console.error('Failed to clear thread:', err);
      showError(err, 'Clearing Thread Messages');
    }
  };

  const handleExportThread = (threadId: number) => {
    const url = api.getExportThreadUrl(threadId);
    window.open(url, '_blank');
  };

  const handleForkMessage = async (messageId: number) => {
    if (!activeThreadId) return;
    try {
      const forkedThread = await api.forkThread(activeThreadId, messageId);
      setThreads((prev) => [...prev, forkedThread]);
      setActiveThreadId(forkedThread.id);
    } catch (err) {
      console.error('Failed to fork thread:', err);
      showError(err, 'Forking Conversation Thread');
    }
  };

  const handleDeleteMessage = async (messageId: number) => {
    const ok = await confirm({
      title: 'Delete Message',
      message: 'Are you sure you want to delete this message from the thread?',
      confirmLabel: 'Delete Message',
      variant: 'danger'
    });
    if (!ok) return;

    try {
      await api.deleteMessage(messageId);
      setMessages((prev) => prev.filter((m) => m.id !== messageId));
      if (activeThreadId) loadThreads();
    } catch (err) {
      console.error('Failed to delete message:', err);
      showError(err, 'Deleting Chat Message');
    }
  };

  const handleToggleCollapse = async (messageId: number) => {
    try {
      const res = await api.toggleMessageCollapse(messageId);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, is_collapsed: res.is_collapsed } : m))
      );
    } catch (err) {
      console.error('Failed to toggle message collapse:', err);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
      {/* Thread Manager Header */}
      <ThreadManager
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={setActiveThreadId}
        onCreateThread={handleCreateThread}
        onRenameThread={handleRenameThread}
        onDeleteThread={handleDeleteThread}
        onClearThread={handleClearThread}
        onExportThread={handleExportThread}
      />

      {/* Scope Context Lens Indicator */}
      {reportId > 0 && activeScope && (
        <div className="px-4 py-1.5 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Context Lens:</span>
            <span className="font-semibold text-slate-200 capitalize">
              {activeScope === 'screen_off' ? 'Screen-Off' : activeScope === 'all' ? 'Full Timeline' : activeScope}
            </span>
          </div>
          <span className="text-slate-500 text-[10px]">Telemetry & prior diagnosis synced</span>
        </div>
      )}

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoadingMessages ? (
          <div className="flex items-center justify-center h-48 text-slate-500 gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-xs">Loading thread history...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">
            No messages in this investigation thread yet. Ask a question below!
          </div>
        ) : (
          messages.map((msg) => (
            <ChatMessageCard
              key={msg.id}
              message={msg}
              onFork={handleForkMessage}
              onDelete={handleDeleteMessage}
              onToggleCollapse={handleToggleCollapse}
            />
          ))
        )}

        {isSending && (
          <div className="flex items-center justify-between gap-3 p-3 bg-indigo-950/30 border border-indigo-800/40 rounded-xl text-xs text-indigo-300 mr-4">
            <div className="flex items-center gap-2 animate-pulse min-w-0">
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-indigo-400" />
              <span className="truncate">AI is analyzing battery dump and composing response...</span>
            </div>
            <button
              type="button"
              onClick={handleCancelSending}
              className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 transition-colors shrink-0"
            >
              🛑 Stop Generation
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSendMessage}
        isLoading={isSending}
        enterMode={effectiveEnterMode}
        onToggleEnterMode={handleToggleEnterMode}
      />
    </div>
  );
};
