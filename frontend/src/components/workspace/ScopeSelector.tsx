import React, { useState, useEffect, useMemo } from 'react';
import { Sliders, RotateCcw, Save, Clock, ChevronDown, ChevronRight } from 'lucide-react';

export type AnalysisScope = 'night' | 'all' | 'screen_off' | 'custom';

interface ScopeSelectorProps {
  currentScope: AnalysisScope;
  onSelectScope: (scope: AnalysisScope) => void;
  isLoading?: boolean;
  nightBounds?: {
    start: string | null;
    end: string | null;
    auto_start?: string | null;
    auto_end?: string | null;
    is_custom?: boolean;
  };
  sessionBounds?: {
    min_time: string | null;
    max_time: string | null;
  };
  customStart?: string;
  customEnd?: string;
  onApplyCustomWindow?: (startIso: string, endIso: string) => void;
  onSaveNightWindow?: (startIso: string, endIso: string) => Promise<void>;
  onResetNightWindow?: () => Promise<void>;
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
    detail: 'Restricts telemetry and diagnostics to a user-defined [start, end] interval within the bugreport timeline.'
  }
];

function toDatetimeLocalValue(iso?: string | null): string {
  if (!iso) return '';
  // Keep local naive timestamp digits YYYY-MM-DDTHH:mm
  const cleaned = iso.replace(' ', 'T');
  return cleaned.slice(0, 16);
}

function formatReadableTs(iso?: string | null): string {
  if (!iso) return 'N/A';
  return iso.replace('T', ' ').slice(0, 16);
}

export const ScopeSelector: React.FC<ScopeSelectorProps> = ({
  currentScope,
  onSelectScope,
  isLoading = false,
  nightBounds,
  sessionBounds,
  customStart,
  customEnd,
  onApplyCustomWindow,
  onSaveNightWindow,
  onResetNightWindow
}) => {
  const activeScopeInfo = SCOPES.find((s) => s.id === currentScope) || SCOPES[0];

  // Night window customization state
  const [showNightEditor, setShowNightEditor] = useState(false);
  const [nightStartInput, setNightStartInput] = useState('');
  const [nightEndInput, setNightEndInput] = useState('');
  const [isSavingNight, setIsSavingNight] = useState(false);

  // Custom window state
  const [customStartInput, setCustomStartInput] = useState('');
  const [customEndInput, setCustomEndInput] = useState('');

  // Sync night inputs when nightBounds change
  useEffect(() => {
    if (nightBounds?.start) {
      setNightStartInput(toDatetimeLocalValue(nightBounds.start));
    }
    if (nightBounds?.end) {
      setNightEndInput(toDatetimeLocalValue(nightBounds.end));
    }
  }, [nightBounds?.start, nightBounds?.end]);

  // Sync custom window inputs when sessionBounds or customStart/customEnd change
  useEffect(() => {
    const defaultStart = customStart || nightBounds?.start || sessionBounds?.min_time;
    const defaultEnd = customEnd || nightBounds?.end || sessionBounds?.max_time;
    if (defaultStart && !customStartInput) {
      setCustomStartInput(toDatetimeLocalValue(defaultStart));
    }
    if (defaultEnd && !customEndInput) {
      setCustomEndInput(toDatetimeLocalValue(defaultEnd));
    }
  }, [customStart, customEnd, nightBounds?.start, nightBounds?.end, sessionBounds?.min_time, sessionBounds?.max_time]);

  // Slider bounds inepoch minutes for quick 15-min scrubbing
  const sliderBounds = useMemo(() => {
    if (!sessionBounds?.min_time || !sessionBounds?.max_time) return null;
    const minMs = new Date(sessionBounds.min_time).getTime();
    const maxMs = new Date(sessionBounds.max_time).getTime();
    if (isNaN(minMs) || isNaN(maxMs) || maxMs <= minMs) return null;
    return {
      minMs,
      maxMs,
      totalMinutes: Math.floor((maxMs - minMs) / 60000),
      minLocal: toDatetimeLocalValue(sessionBounds.min_time),
      maxLocal: toDatetimeLocalValue(sessionBounds.max_time)
    };
  }, [sessionBounds?.min_time, sessionBounds?.max_time]);

  const inputToOffsetMinutes = (val: string, fallbackOffset: number): number => {
    if (!sliderBounds || !val) return fallbackOffset;
    const ms = new Date(val).getTime();
    if (isNaN(ms)) return fallbackOffset;
    return Math.max(0, Math.min(sliderBounds.totalMinutes, Math.round((ms - sliderBounds.minMs) / 60000)));
  };

  const offsetMinutesToLocalStr = (offsetMin: number): string => {
    if (!sliderBounds) return '';
    const d = new Date(sliderBounds.minMs + offsetMin * 60000);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
  };

  const handleSaveNight = async () => {
    if (!onSaveNightWindow || !nightStartInput || !nightEndInput) return;
    setIsSavingNight(true);
    try {
      await onSaveNightWindow(`${nightStartInput}:00`, `${nightEndInput}:00`);
    } finally {
      setIsSavingNight(false);
    }
  };

  const handleResetNight = async () => {
    if (!onResetNightWindow) return;
    setIsSavingNight(true);
    try {
      await onResetNightWindow();
    } finally {
      setIsSavingNight(false);
    }
  };

  const handleApplyCustom = () => {
    if (!onApplyCustomWindow || !customStartInput || !customEndInput) return;
    onApplyCustomWindow(`${customStartInput}:00`, `${customEndInput}:00`);
  };

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
      <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs text-slate-400 flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-start gap-2.5">
          <span className="text-base mt-0.5">{activeScopeInfo.icon}</span>
          <div>
            <span className="font-semibold text-slate-200 mr-1.5">{activeScopeInfo.label}:</span>
            <span>{activeScopeInfo.detail}</span>
          </div>
        </div>

        {currentScope === 'night' && nightBounds?.start && nightBounds?.end && (
          <div className="flex items-center gap-2 shrink-0">
            <span className="px-2.5 py-1 rounded-md bg-indigo-950/70 border border-indigo-500/30 text-indigo-200 font-mono text-[11px]">
              🌙 {formatReadableTs(nightBounds.start)} → {formatReadableTs(nightBounds.end)}
            </span>
            {nightBounds.is_custom && (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Custom Saved
              </span>
            )}
          </div>
        )}
      </div>

      {/* Night Drain Customization Expander */}
      {currentScope === 'night' && (
        <div className="border border-slate-800/90 rounded-lg bg-slate-950/50 overflow-hidden">
          <button
            type="button"
            onClick={() => setShowNightEditor(!showNightEditor)}
            className="w-full flex items-center justify-between px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900/50 transition-colors"
          >
            <span className="flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-indigo-400" />
              <span>⏱️ Adjust Night Sleep/Wake Window for this Report</span>
              {nightBounds?.is_custom && (
                <span className="text-[10px] text-amber-400">(Customized)</span>
              )}
            </span>
            {showNightEditor ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          </button>

          {showNightEditor && (
            <div className="p-3.5 border-t border-slate-800/80 space-y-3 bg-slate-950/80">
              <p className="text-[11px] text-slate-400">
                Customize the exact bedtime and wake-up timestamps for this report session. Saving persists these bounds to the database for KPI metrics, charts, and AI diagnoses.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Bedtime Start */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-slate-300">
                    🌙 Bedtime (Start): <span className="font-mono text-indigo-300">{nightStartInput.replace('T', ' ')}</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={nightStartInput}
                    min={sliderBounds?.minLocal}
                    max={sliderBounds?.maxLocal}
                    onChange={(e) => setNightStartInput(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                  {sliderBounds && (
                    <input
                      type="range"
                      min={0}
                      max={sliderBounds.totalMinutes}
                      step={15}
                      value={inputToOffsetMinutes(nightStartInput, 0)}
                      onChange={(e) => setNightStartInput(offsetMinutesToLocalStr(Number(e.target.value)))}
                      className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                    />
                  )}
                </div>

                {/* Wake-up End */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium text-slate-300">
                    ☀️ Wake-up (End): <span className="font-mono text-indigo-300">{nightEndInput.replace('T', ' ')}</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={nightEndInput}
                    min={sliderBounds?.minLocal}
                    max={sliderBounds?.maxLocal}
                    onChange={(e) => setNightEndInput(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                  {sliderBounds && (
                    <input
                      type="range"
                      min={0}
                      max={sliderBounds.totalMinutes}
                      step={15}
                      value={inputToOffsetMinutes(nightEndInput, sliderBounds.totalMinutes)}
                      onChange={(e) => setNightEndInput(offsetMinutesToLocalStr(Number(e.target.value)))}
                      className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                    />
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <div className="text-[11px] text-slate-500">
                  {nightBounds?.auto_start && nightBounds?.auto_end && (
                    <span>
                      Auto-detected window: <code className="text-slate-400">{formatReadableTs(nightBounds.auto_start)} → {formatReadableTs(nightBounds.auto_end)}</code>
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleResetNight}
                    disabled={isSavingNight || !nightBounds?.is_custom}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reset to Detected Window
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveNight}
                    disabled={isSavingNight || !nightStartInput || !nightEndInput}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors"
                  >
                    <Save className="w-3.5 h-3.5" />
                    {isSavingNight ? 'Saving...' : 'Apply & Save Window'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Custom Window Time Range Picker */}
      {currentScope === 'custom' && (
        <div className="p-3.5 border border-indigo-500/30 rounded-lg bg-slate-950/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              Select Custom Analysis Time Window
            </span>
            {sessionBounds?.min_time && sessionBounds?.max_time && (
              <span className="text-[11px] text-slate-400 font-mono">
                Session bounds: {formatReadableTs(sessionBounds.min_time)} → {formatReadableTs(sessionBounds.max_time)}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-slate-300">
                Start Time: <span className="font-mono text-indigo-300">{customStartInput.replace('T', ' ')}</span>
              </label>
              <input
                type="datetime-local"
                value={customStartInput}
                min={sliderBounds?.minLocal}
                max={sliderBounds?.maxLocal}
                onChange={(e) => setCustomStartInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
              />
              {sliderBounds && (
                <input
                  type="range"
                  min={0}
                  max={sliderBounds.totalMinutes}
                  step={15}
                  value={inputToOffsetMinutes(customStartInput, 0)}
                  onChange={(e) => setCustomStartInput(offsetMinutesToLocalStr(Number(e.target.value)))}
                  className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              )}
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-slate-300">
                End Time: <span className="font-mono text-indigo-300">{customEndInput.replace('T', ' ')}</span>
              </label>
              <input
                type="datetime-local"
                value={customEndInput}
                min={sliderBounds?.minLocal}
                max={sliderBounds?.maxLocal}
                onChange={(e) => setCustomEndInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
              />
              {sliderBounds && (
                <input
                  type="range"
                  min={0}
                  max={sliderBounds.totalMinutes}
                  step={15}
                  value={inputToOffsetMinutes(customEndInput, sliderBounds.totalMinutes)}
                  onChange={(e) => setCustomEndInput(offsetMinutesToLocalStr(Number(e.target.value)))}
                  className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleApplyCustom}
              disabled={isLoading || !customStartInput || !customEndInput}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50 transition-colors"
            >
              <Clock className="w-3.5 h-3.5" />
              Apply Custom Window
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
