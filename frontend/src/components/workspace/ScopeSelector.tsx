import React from 'react';

export type AnalysisScope = 'night' | 'all' | 'screen_off' | 'custom';

interface ScopeSelectorProps {
  currentScope: AnalysisScope;
  onSelectScope: (scope: AnalysisScope) => void;
  isLoading?: boolean;
}

const SCOPES: { id: AnalysisScope; label: string; icon: string; desc: string; detail: string }[] = [
  {
    id: 'night',
    label: 'Night Drain',
    icon: '🌙',
    desc: 'Deep sleep & overnight drain',
    detail: 'Isolates configured night window (default 23:00 - 07:00). Exposes standby battery drain, ambient leaks, and rogue alarms.'
  },
  {
    id: 'all',
    label: 'Full Timeline',
    icon: '📊',
    desc: 'Entire bugreport timeline',
    detail: 'Evaluates entire captured dataset without any time filtering or clamp boundaries. Best for global trends.'
  },
  {
    id: 'screen_off',
    label: 'Screen Off',
    icon: '📱',
    desc: 'Display inactive periods',
    detail: 'Filters timeline to only intervals where the display was powered off. Exposes background wakelocks and chatter.'
  },
  {
    id: 'custom',
    label: 'Custom Window',
    icon: '⏱️',
    desc: 'User-specified time clamp',
    detail: 'Restricts telemetry and diagnostics to a user-defined [start, end] interval or saved report night bounds.'
  }
];

export const ScopeSelector: React.FC<ScopeSelectorProps> = ({
  currentScope,
  onSelectScope,
  isLoading = false
}) => {
  const activeScopeInfo = SCOPES.find((s) => s.id === currentScope) || SCOPES[0];

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Analysis Scope
        </span>
        {isLoading && (
          <span className="text-xs text-indigo-400 animate-pulse">
            Recalculating telemetry...
          </span>
        )}
      </div>

      {/* 4 Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {SCOPES.map((scope) => {
          const isActive = currentScope === scope.id;
          return (
            <button
              key={scope.id}
              onClick={() => onSelectScope(scope.id)}
              disabled={isLoading}
              className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left border ${
                isActive
                  ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 shadow-sm shadow-indigo-500/10'
                  : 'bg-slate-800/40 border-slate-700/60 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
              } disabled:opacity-50`}
            >
              <span className="text-base">{scope.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">{scope.label}</div>
                <div className="text-[10px] text-slate-400 truncate">{scope.desc}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Full-width informative guide panel */}
      <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs text-slate-400 flex items-start gap-2.5">
        <span className="text-base mt-0.5">{activeScopeInfo.icon}</span>
        <div>
          <span className="font-semibold text-slate-200 mr-1.5">{activeScopeInfo.label}:</span>
          <span>{activeScopeInfo.detail}</span>
        </div>
      </div>
    </div>
  );
};
