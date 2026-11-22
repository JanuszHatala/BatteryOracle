import React, { createContext, useContext, useState, useCallback } from 'react';
import {
  AlertTriangle,
  X,
  Settings as SettingsIcon,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  ShieldAlert,
  CheckCircle2,
  Info
} from 'lucide-react';
import { AiErrorDetail } from '../../types/api';
import { ApiClientError } from '../../api/client';

interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'primary';
}

interface NoticeOptions {
  title: string;
  message: string;
  variant?: 'info' | 'success' | 'warning';
}

interface DialogContextValue {
  showError: (err: unknown, actionDesc?: string) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  showNotice: (options: NoticeOptions) => void;
}

const DialogContext = createContext<DialogContextValue | null>(null);

export const useDialog = (): DialogContextValue => {
  const ctx = useContext(DialogContext);
  if (!ctx) {
    throw new Error('useDialog must be used within a DialogProvider');
  }
  return ctx;
};

function parseClientFallbackError(err: unknown): AiErrorDetail {
  if (err instanceof ApiClientError && err.aiError) {
    return err.aiError;
  }

  const raw = err instanceof Error ? err.message : String(err || 'Unknown error');
  const lower = raw.toLowerCase();

  if (lower.includes('429') || lower.includes('rate_limit') || lower.includes('ratelimit') || lower.includes('resource_exhausted') || lower.includes('quota')) {
    const isDaily = lower.includes('perday') || lower.includes('per_day') || lower.includes('daily');
    return {
      category: isDaily ? 'quota_exceeded' : 'rate_limit',
      title: isDaily ? 'Daily Free Tier Quota Exhausted (429)' : 'API Rate Limit Reached (429)',
      icon: '⏳',
      raw_error: raw,
      suggestions: isDaily
        ? [
            'Daily Free Tier Quota Exhausted: Switch to another model (e.g. gemini-3-flash-preview or gemini-3.1-flash-lite-preview) in Settings -> AI & LLM Engine.',
            'Alternatively, switch to OpenRouter or upgrade your API billing tier.'
          ]
        : [
            'Wait 30-60 seconds and click the action button again.',
            'Switch to a faster/lighter model or another provider in Settings -> AI & LLM Engine.'
          ],
      retry_delay_sec: null,
      rate_limit_meta: { is_daily_quota: isDaily, is_free_tier: lower.includes('free_tier') }
    };
  }

  if (lower.includes('503') || lower.includes('unavailable') || lower.includes('overloaded') || lower.includes('high demand')) {
    return {
      category: 'connection',
      title: 'Model Experiencing High Demand (503 Unavailable)',
      icon: '🌐',
      raw_error: raw,
      suggestions: [
        'The upstream AI provider is experiencing a temporary traffic spike on this model.',
        'Wait 15-30 seconds and retry, or switch to an alternative model (e.g. gemini-3-flash-preview or gemini-3.1-flash-lite-preview) in Settings -> AI & LLM Engine.'
      ],
      retry_delay_sec: 15,
      rate_limit_meta: {}
    };
  }

  if (lower.includes('401') || lower.includes('403') || lower.includes('api_key') || lower.includes('unauthorized')) {
    return {
      category: 'auth',
      title: 'Authentication / API Key Error',
      icon: '🔑',
      raw_error: raw,
      suggestions: [
        'Verify your API key in Settings -> AI & LLM Engine.',
        'Click "Test Connection" in Settings to verify credentials.'
      ],
      retry_delay_sec: null,
      rate_limit_meta: {}
    };
  }

  return {
    category: 'unknown',
    title: 'Operation Failed',
    icon: '⚠️',
    raw_error: raw,
    suggestions: [
      'Check the technical error details below.',
      'If this is an AI model error, verify your active provider and model in Settings -> AI & LLM Engine.'
    ],
    retry_delay_sec: null,
    rate_limit_meta: {}
  };
}

interface DialogProviderProps {
  children: React.ReactNode;
  onOpenSettings?: () => void;
}

export const DialogProvider: React.FC<DialogProviderProps> = ({ children, onOpenSettings }) => {
  // Error modal state
  const [errorState, setErrorState] = useState<{ detail: AiErrorDetail; actionDesc?: string } | null>(null);
  const [showRawTrace, setShowRawTrace] = useState(false);

  // Confirm modal state
  const [confirmState, setConfirmState] = useState<{
    options: ConfirmOptions;
    resolve: (val: boolean) => void;
  } | null>(null);

  // Notice modal state
  const [noticeState, setNoticeState] = useState<NoticeOptions | null>(null);

  const showError = useCallback((err: unknown, actionDesc?: string) => {
    const detail = parseClientFallbackError(err);
    setShowRawTrace(false);
    setErrorState({ detail, actionDesc });
  }, []);

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      setConfirmState({ options, resolve });
    });
  }, []);

  const showNotice = useCallback((options: NoticeOptions) => {
    setNoticeState(options);
  }, []);

  const handleConfirmClose = (result: boolean) => {
    if (confirmState) {
      confirmState.resolve(result);
      setConfirmState(null);
    }
  };

  return (
    <DialogContext.Provider value={{ showError, confirm, showNotice }}>
      {children}

      {/* AI & System Error Diagnostic Modal */}
      {errorState && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-rose-500/30 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-start justify-between px-6 py-4 bg-rose-950/25 border-b border-rose-500/20">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-xl shrink-0">
                  {errorState.detail.icon || '⚠️'}
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-bold text-slate-100">
                      {errorState.detail.title}
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      {errorState.detail.category.replace('_', ' ')}
                    </span>
                  </div>
                  {errorState.actionDesc && (
                    <p className="text-xs text-slate-400 mt-0.5">
                      While trying to: <span className="text-slate-200 font-medium">{errorState.actionDesc}</span>
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={() => setErrorState(null)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              {/* Rate Limit / Quota Callout */}
              {(errorState.detail.category === 'rate_limit' || errorState.detail.category === 'quota_exceeded' || errorState.detail.retry_delay_sec) && (
                <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200 space-y-2">
                  {errorState.detail.rate_limit_meta?.is_daily_quota ? (
                    <div className="font-semibold text-amber-300 flex items-center gap-1.5">
                      <span>🛑 Daily Free Tier Quota Reached</span>
                      {errorState.detail.rate_limit_meta.model && (
                        <code className="px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-200 font-mono">
                          {errorState.detail.rate_limit_meta.model}
                        </code>
                      )}
                      {errorState.detail.rate_limit_meta.quota_limit && (
                        <span className="text-amber-400/90">
                          (Limit: {errorState.detail.rate_limit_meta.quota_limit} req/day)
                        </span>
                      )}
                    </div>
                  ) : errorState.detail.retry_delay_sec ? (
                    <div className="font-semibold text-amber-300">
                      ⏱️ Provider requested a wait of ~{Math.ceil(errorState.detail.retry_delay_sec)} seconds before retrying.
                    </div>
                  ) : (
                    <div className="font-semibold text-amber-300">
                      ⏱️ Upstream API rate or capacity limit triggered.
                    </div>
                  )}

                  {errorState.detail.raw_error.toLowerCase().includes('gemini') && (
                    <div className="flex items-center gap-4 pt-1 text-[11px] text-amber-300/90">
                      <a
                        href="https://ai.dev/rate-limit"
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 underline hover:text-amber-100"
                      >
                        📊 Google AI Studio Rate Limits <ExternalLink className="w-3 h-3" />
                      </a>
                      <a
                        href="https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas"
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 underline hover:text-amber-100"
                      >
                        ☁️ Google Cloud Quotas <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              )}

              {/* Recommended Next Steps */}
              {errorState.detail.suggestions && errorState.detail.suggestions.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    💡 Recommended Next Steps
                  </div>
                  <ul className="space-y-1.5 text-xs text-slate-300 bg-slate-950/60 border border-slate-800 rounded-xl p-3.5">
                    {errorState.detail.suggestions.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 leading-relaxed">
                        <span className="text-indigo-400 font-bold mt-0.5">•</span>
                        <span>{s.replace(/\*\*/g, '')}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Raw Technical Error Expander */}
              <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/50">
                <button
                  type="button"
                  onClick={() => setShowRawTrace(!showRawTrace)}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 transition-colors"
                >
                  <span>🔍 View Raw Error Details & Technical Trace</span>
                  {showRawTrace ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
                {showRawTrace && (
                  <pre className="p-3.5 text-[11px] font-mono text-rose-300/90 bg-slate-950 border-t border-slate-800 overflow-x-auto whitespace-pre-wrap break-words max-h-48">
                    {errorState.detail.raw_error}
                  </pre>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-6 py-3.5 bg-slate-950/80 border-t border-slate-800">
              {onOpenSettings ? (
                <button
                  type="button"
                  onClick={() => {
                    setErrorState(null);
                    onOpenSettings();
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-colors"
                >
                  <SettingsIcon className="w-3.5 h-3.5" />
                  Open AI & LLM Settings
                </button>
              ) : <div />}

              <button
                type="button"
                onClick={() => setErrorState(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Confirmation Modal */}
      {confirmState && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-6">
              <div className="flex items-start gap-3.5">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                    confirmState.options.variant === 'danger'
                      ? 'bg-rose-500/15 border-rose-500/30 text-rose-400'
                      : confirmState.options.variant === 'warning'
                      ? 'bg-amber-500/15 border-amber-500/30 text-amber-400'
                      : 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400'
                  }`}
                >
                  {confirmState.options.variant === 'danger' ? (
                    <ShieldAlert className="w-5 h-5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-bold text-slate-100">
                    {confirmState.options.title}
                  </h3>
                  <p className="text-xs text-slate-300 mt-1.5 leading-relaxed whitespace-pre-line">
                    {confirmState.options.message}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 px-6 py-3.5 bg-slate-950/80 border-t border-slate-800">
              <button
                type="button"
                onClick={() => handleConfirmClose(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                {confirmState.options.cancelLabel || 'Cancel'}
              </button>
              <button
                type="button"
                onClick={() => handleConfirmClose(true)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold text-white transition-colors ${
                  confirmState.options.variant === 'danger'
                    ? 'bg-rose-600 hover:bg-rose-500'
                    : confirmState.options.variant === 'warning'
                    ? 'bg-amber-600 hover:bg-amber-500'
                    : 'bg-indigo-600 hover:bg-indigo-500'
                }`}
              >
                {confirmState.options.confirmLabel || 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Notice Modal */}
      {noticeState && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-6">
              <div className="flex items-start gap-3.5">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                    noticeState.variant === 'success'
                      ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                      : noticeState.variant === 'warning'
                      ? 'bg-amber-500/15 border-amber-500/30 text-amber-400'
                      : 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400'
                  }`}
                >
                  {noticeState.variant === 'success' ? (
                    <CheckCircle2 className="w-5 h-5" />
                  ) : noticeState.variant === 'warning' ? (
                    <AlertTriangle className="w-5 h-5" />
                  ) : (
                    <Info className="w-5 h-5" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-bold text-slate-100">{noticeState.title}</h3>
                  <p className="text-xs text-slate-300 mt-1.5 leading-relaxed whitespace-pre-line">
                    {noticeState.message}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end px-6 py-3.5 bg-slate-950/80 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setNoticeState(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </DialogContext.Provider>
  );
};
