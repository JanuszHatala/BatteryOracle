import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Thread, Message } from '../../types/api';
import { api } from '../../api/client';
import { ThreadManager } from './ThreadManager';
import { ChatMessageCard } from './ChatMessageCard';
import { ChatInput } from './ChatInput';
import { Loader2 } from 'lucide-react';

interface ChatWorkspaceProps {
  reportId: number;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({ reportId }) => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [enterMode, setEnterMode] = useState<'newline' | 'send'>('send');

  const messagesEndRef = useRef<HTMLDivElement>(null);

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

    try {
      await api.sendMessage(activeThreadId, prompt);
      await loadMessages(activeThreadId);
      await loadThreads();
    } catch (err) {
      console.error('Failed to send message:', err);
      alert('Failed to send message to AI.');
    } finally {
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
    }
  };

  const handleRenameThread = async (threadId: number, newTitle: string) => {
    try {
      const updated = await api.renameThread(threadId, newTitle);
      setThreads((prev) => prev.map((t) => (t.id === threadId ? updated : t)));
    } catch (err) {
      console.error('Failed to rename thread:', err);
    }
  };

  const handleDeleteThread = async (threadId: number) => {
    if (!confirm('Are you sure you want to delete this conversation thread?')) return;
    try {
      await api.deleteThread(threadId);
      const remaining = threads.filter((t) => t.id !== threadId);
      setThreads(remaining);
      setActiveThreadId(remaining.length > 0 ? remaining[0].id : null);
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
  };

  const handleClearThread = async (threadId: number) => {
    if (!confirm('Clear all messages in this thread?')) return;
    try {
      await api.clearThread(threadId);
      setMessages([]);
      await loadThreads();
    } catch (err) {
      console.error('Failed to clear thread:', err);
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
    }
  };

  const handleDeleteMessage = async (messageId: number) => {
    try {
      await api.deleteMessage(messageId);
      setMessages((prev) => prev.filter((m) => m.id !== messageId));
      if (activeThreadId) loadThreads();
    } catch (err) {
      console.error('Failed to delete message:', err);
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
          <div className="flex items-center gap-2 p-3 bg-indigo-950/20 border border-indigo-800/30 rounded-xl text-xs text-indigo-300 animate-pulse mr-4">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>AI is analyzing battery dump and composing response...</span>
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
        enterMode={enterMode}
        onToggleEnterMode={() => setEnterMode(enterMode === 'send' ? 'newline' : 'send')}
      />
    </div>
  );
};
