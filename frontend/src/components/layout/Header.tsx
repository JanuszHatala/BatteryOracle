import React from 'react';
import { Button } from '../ui/Button';
import {
  Zap,
  Upload,
  Settings as SettingsIcon,
  GitCompare,
  Columns,
  Rows,
  ExternalLink,
  FileText,
  Smartphone,
  FlaskConical,
  Coins,
  Bot,
  Globe
} from 'lucide-react';
import { Settings } from '../../types/api';

export type ChatLayoutMode = 'split' | 'stacked' | 'floating' | 'hidden';
export type WorkspaceViewMode = 'single' | 'compare' | 'profile' | 'master' | 'accounting';

interface HeaderProps {
  settings: Settings | null;
  onOpenUpload: () => void;
  onOpenSettings: () => void;
  workspaceView: WorkspaceViewMode;
  onSelectWorkspaceView: (view: WorkspaceViewMode) => void;
  selectedCount: number;
  chatLayout: ChatLayoutMode;
  onSelectChatLayout: (mode: ChatLayoutMode) => void;
}

const WORKSPACE_TABS: { id: WorkspaceViewMode; label: string; shortLabel: string; icon: React.ReactNode }[] = [
  { id: 'single', label: 'Single Report', shortLabel: 'Single', icon: <FileText className="w-3.5 h-3.5" /> },
  { id: 'compare', label: 'Merged & Compare', shortLabel: 'Compare', icon: <GitCompare className="w-3.5 h-3.5" /> },
  { id: 'profile', label: 'Device Profile & Audit', shortLabel: 'Profile & Routers', icon: <Smartphone className="w-3.5 h-3.5" /> },
  { id: 'master', label: 'Master Synthesis', shortLabel: 'Synthesis', icon: <FlaskConical className="w-3.5 h-3.5" /> },
  { id: 'accounting', label: 'Token & Cost Accounting', shortLabel: 'Accounting', icon: <Coins className="w-3.5 h-3.5" /> }
];

export const Header: React.FC<HeaderProps> = ({
  settings,
  onOpenUpload,
  onOpenSettings,
  workspaceView,
  onSelectWorkspaceView,
  selectedCount,
  chatLayout,
  onSelectChatLayout
}) => {
  return (
    <header className="min-h-14 py-1.5 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-3 sm:px-4 flex items-center justify-between gap-2 shrink-0 select-none z-20 overflow-hidden">
      {/* Left: Brand Logo */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-950 shrink-0">
          <Zap className="w-4 h-4" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-bold text-slate-100 text-sm tracking-tight hidden sm:inline">BatteryOracle</span>
          <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60">2.0</span>
        </div>
      </div>

      {/* Center: 5-Mode Workspace View Switcher */}
      <div className="flex items-center bg-slate-950/90 border border-slate-800 rounded-xl p-1 gap-0.5 sm:gap-1 overflow-x-auto min-w-0 max-w-fit">
        {WORKSPACE_TABS.map((tab) => {
          const isActive = workspaceView === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectWorkspaceView(tab.id)}
              className={`px-2 sm:px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 whitespace-nowrap cursor-pointer shrink-0 ${
                isActive
                  ? 'bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
              }`}
              title={tab.label}
            >
              {tab.icon}
              <span className="hidden xl:inline">{tab.label}</span>
              <span className="xl:hidden hidden md:inline">{tab.shortLabel}</span>
              {tab.id === 'compare' && selectedCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/30 text-emerald-200 font-bold">
                  {selectedCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Right: Engine Status Pill + Chat Layout + Upload + Settings */}
      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
        {settings && (
          <button
            onClick={onOpenSettings}
            title={`LLM Provider: ${settings.active_llm_provider}\nModel: ${settings.active_llm_model}\nTimezone: ${settings.device_timezone}`}
            className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500/50 text-xs transition-colors cursor-pointer min-w-0"
          >
            <span className="flex items-center gap-1 text-indigo-300 font-medium min-w-0">
              <Bot className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="hidden 2xl:inline shrink-0">{settings.active_llm_provider}:</span>
              <code className="font-mono text-[11px] text-emerald-400 bg-slate-900 px-1 py-0.5 rounded truncate max-w-[100px] xl:max-w-[160px] 2xl:max-w-[220px]">
                {settings.active_llm_model}
              </code>
            </span>
            <span className="text-slate-600 hidden 2xl:inline">•</span>
            <span className="hidden 2xl:flex items-center gap-1 text-slate-300 font-mono text-[11px] shrink-0">
              <Globe className="w-3 h-3 text-sky-400" />
              {settings.device_timezone}
            </span>
          </button>
        )}

        {/* 3-State Chat Layout Switcher (when in Single Report view) */}
        {workspaceView === 'single' && (
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs shrink-0">
            <button
              onClick={() => onSelectChatLayout('split')}
              className={`p-1.5 rounded transition-colors flex items-center gap-1 cursor-pointer ${
                chatLayout === 'split' ? 'bg-indigo-600/30 text-indigo-300' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Side-by-side Layout"
            >
              <Columns className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => onSelectChatLayout('stacked')}
              className={`p-1.5 rounded transition-colors flex items-center gap-1 cursor-pointer ${
                chatLayout === 'stacked' ? 'bg-indigo-600/30 text-indigo-300' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Stacked Layout"
            >
              <Rows className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => onSelectChatLayout('floating')}
              className={`p-1.5 rounded transition-colors flex items-center gap-1 cursor-pointer ${
                chatLayout === 'floating' ? 'bg-indigo-600/30 text-indigo-300' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Floating Window"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <Button
          variant="primary"
          size="sm"
          onClick={onOpenUpload}
          className="text-xs bg-emerald-600 hover:bg-emerald-500 px-2 sm:px-2.5 shrink-0"
        >
          <Upload className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Upload</span>
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={onOpenSettings}
          className="text-xs px-2 sm:px-2.5 shrink-0"
          title="Configure LLM & Prompts Studio"
        >
          <SettingsIcon className="w-3.5 h-3.5 text-indigo-400" />
          <span className="hidden xl:inline">LLM & Prompts</span>
        </Button>
      </div>
    </header>
  );
};
