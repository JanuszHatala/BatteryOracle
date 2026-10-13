import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import { api } from '../../api/client';
import {
  Settings,
  ModelsResponse,
  ModelItemDetail,
  ProviderPresetInfo,
  PromptsMap
} from '../../types/api';
import {
  Sliders,
  Key,
  Check,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  Trash2,
  FileCode,
  RotateCcw,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSettings: Settings | null;
  onSettingsUpdated: (newSettings: Settings) => void;
}

const DEFAULT_PROVIDERS: ProviderPresetInfo[] = [
  { name: 'Google Gemini', default_model: 'gemini/gemini-3.8-flash', default_base: null, requires_key: true },
  { name: 'OpenAI', default_model: 'openai/gpt-4o', default_base: null, requires_key: true },
  { name: 'Anthropic', default_model: 'anthropic/claude-3-7-sonnet-latest', default_base: null, requires_key: true },
  { name: 'Groq', default_model: 'groq/llama-3.3-70b-versatile', default_base: null, requires_key: true },
  { name: 'Mistral AI', default_model: 'mistral/mistral-large-latest', default_base: null, requires_key: true },
  { name: 'OpenRouter', default_model: 'openrouter/google/gemini-2.5-pro', default_base: 'https://openrouter.ai/api/v1', requires_key: true },
  { name: 'DeepSeek', default_model: 'deepseek/deepseek-chat', default_base: 'https://api.deepseek.com/v1', requires_key: true },
  { name: 'Ollama (Local)', default_model: 'ollama/llama3.2', default_base: 'http://localhost:11434', requires_key: false }
];

const COMMON_TIMEZONES = [
  'Europe/Warsaw',
  'UTC',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Asia/Seoul',
  'Asia/Shanghai',
  'Asia/Singapore',
  'Asia/Kolkata',
  'Australia/Sydney'
];

const PROMPT_LABELS: { key: keyof PromptsMap; label: string; desc: string }[] = [
  { key: 'single_diagnosis', label: '1. Single Report Diagnosis', desc: 'System prompt for single bugreport diagnostic telemetry analysis.' },
  { key: 'comparison', label: '2. Multi-Report Comparison', desc: 'System prompt for comparative & merged timeline regression analysis.' },
  { key: 'chat_assistant', label: '3. Interactive Chat Assistant', desc: 'System prompt for interactive investigation chat threads.' },
  { key: 'master_synthesis', label: '4. Master Synthesis & Blueprint', desc: 'System prompt for cross-report Master Synthesis & Action Plan.' },
  { key: 'profile_audit', label: '5. Device Profile Audit', desc: 'System prompt for auditing live ADB device configuration & Doze parameters.' },
  { key: 'profile_comparison', label: '6. Device Profile Comparison', desc: 'System prompt for diffing two device configuration snapshots.' },
  { key: 'profile_chat', label: '7. Profile Consultation Chat', desc: 'System prompt for interactive Device Profile & WiFi Router consultation.' }
];

const CUSTOM_MODEL_SENTINEL = '__TYPE_CUSTOM_MODEL__';

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentSettings,
  onSettingsUpdated
}) => {
  const [activeTab, setActiveTab] = useState<'llm' | 'prompts' | 'preferences'>('llm');

  // Tab 1: LLM Provider & Credentials state
  const [provider, setProvider] = useState('Google Gemini');
  const [selectedModelOption, setSelectedModelOption] = useState('gemini/gemini-3.8-flash');
  const [customTypedModel, setCustomTypedModel] = useState('');
  const [modelDetails, setModelDetails] = useState<ModelItemDetail[]>([]);
  const [apiKey, setApiKey] = useState('');
  const [apiBase, setApiBase] = useState('');

  // Live models & custom model registration state
  const [fetchingLive, setFetchingLive] = useState(false);
  const [liveFetchMsg, setLiveFetchMsg] = useState<string | null>(null);
  const [showCustomManager, setShowCustomManager] = useState(false);
  const [newCustomModelId, setNewCustomModelId] = useState('');
  const [customSaving, setCustomSaving] = useState(false);

  // Tab 2: Prompts state
  const [prompts, setPrompts] = useState<PromptsMap | null>(null);
  const [activePromptKey, setActivePromptKey] = useState<keyof PromptsMap>('single_diagnosis');
  const [savingPrompts, setSavingPrompts] = useState(false);
  const [promptsMsg, setPromptsMsg] = useState<string | null>(null);

  // Tab 3: Regional & Night Standby state
  const [timezone, setTimezone] = useState('Europe/Warsaw');
  const [nightStart, setNightStart] = useState(23);
  const [nightEnd, setNightEnd] = useState(7);
  const [enterMode, setEnterMode] = useState<'newline' | 'send'>('newline');

  // Action states
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const providersList =
    currentSettings?.providers && currentSettings.providers.length > 0
      ? currentSettings.providers
      : DEFAULT_PROVIDERS;

  const activeFinalModel =
    selectedModelOption === CUSTOM_MODEL_SENTINEL
      ? customTypedModel.trim()
      : selectedModelOption;

  // Sync settings into modal state on open
  useEffect(() => {
    if (currentSettings && isOpen) {
      const prov = currentSettings.active_llm_provider || 'Google Gemini';
      const mod = currentSettings.active_llm_model || 'gemini/gemini-3.8-flash';
      setProvider(prov);
      setSelectedModelOption(mod);
      setApiBase(currentSettings.llm_api_base || '');
      setTimezone(currentSettings.device_timezone || 'Europe/Warsaw');
      setNightStart(currentSettings.night_start_hour ?? 23);
      setNightEnd(currentSettings.night_end_hour ?? 7);
      setEnterMode(currentSettings.chat_enter_mode || 'newline');
      setApiKey('');
      setTestResult(null);
      setLiveFetchMsg(null);
    }
  }, [currentSettings, isOpen]);

  // Load models when provider changes or modal opens
  const loadProviderModels = async (prov: string, preferredModel?: string) => {
    try {
      const res: ModelsResponse = await api.getModels(prov);
      const details = res.model_details || [];
      setModelDetails(details);

      const targetModel = preferredModel ?? selectedModelOption;
      const existsInDetails = details.some((d) => d.id === targetModel);
      if (existsInDetails) {
        setSelectedModelOption(targetModel);
      } else if (
        targetModel &&
        targetModel !== CUSTOM_MODEL_SENTINEL &&
        prov === currentSettings?.active_llm_provider
      ) {
        setModelDetails([
          { id: targetModel, pricing: 'Custom / Saved', is_custom: true },
          ...details
        ]);
        setSelectedModelOption(targetModel);
      } else if (details.length > 0) {
        setSelectedModelOption(res.default_model || details[0].id);
      }
    } catch (err) {
      console.error('Failed to load models for provider:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadProviderModels(
        provider,
        provider === currentSettings?.active_llm_provider
          ? currentSettings?.active_llm_model
          : undefined
      );
    }
  }, [provider, isOpen]);

  // Load prompts when Prompt Studio tab is opened
  useEffect(() => {
    if (isOpen && activeTab === 'prompts' && !prompts) {
      api
        .getPrompts()
        .then((res) => setPrompts(res.prompts))
        .catch((err) => console.error('Failed to load prompts:', err));
    }
  }, [isOpen, activeTab, prompts]);

  const handleProviderChange = (newProv: string) => {
    setProvider(newProv);
    const preset = providersList.find((p) => p.name === newProv);
    if (preset) {
      setApiBase(preset.default_base || '');
      setSelectedModelOption(preset.default_model);
    }
    setLiveFetchMsg(null);
  };

  const formatModelLabel = (m: ModelItemDetail): string => {
    return `${m.id}  [${m.pricing || 'Pricing N/A'}]${m.is_custom ? ' ★' : ''}`;
  };

  const handleFetchLiveModels = async () => {
    setFetchingLive(true);
    setLiveFetchMsg(null);
    try {
      const res = await api.fetchLiveModels(
        provider,
        apiKey.trim() || undefined,
        apiBase.trim() || undefined
      );
      if (res.model_details && res.model_details.length > 0) {
        setModelDetails(res.model_details);
      }
      setLiveFetchMsg(res.message || `Fetched ${res.models.length} models.`);
    } catch (err: any) {
      setLiveFetchMsg(`Error: ${err.message || 'Failed to fetch live models'}`);
    } finally {
      setFetchingLive(false);
    }
  };

  const handleAddCustomModel = async () => {
    if (!newCustomModelId.trim()) return;
    setCustomSaving(true);
    try {
      const addedId = newCustomModelId.trim();
      const res = await api.addCustomModel(provider, addedId);
      setNewCustomModelId('');
      setModelDetails(res.model_details || []);
      setSelectedModelOption(addedId);
    } catch (err: any) {
      alert(`Failed to add custom model: ${err.message}`);
    } finally {
      setCustomSaving(false);
    }
  };

  const handleDeleteCustomModel = async (modelId: string) => {
    try {
      const res = await api.deleteCustomModel(provider, modelId);
      setModelDetails(res.model_details || []);
    } catch (err: any) {
      alert(`Failed to delete custom model: ${err.message}`);
    }
  };

  const handleTestConnection = async () => {
    if (!activeFinalModel) {
      setTestResult({ success: false, message: 'Please select or enter a Model ID.' });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConnection(
        activeFinalModel,
        provider,
        apiKey.trim() || undefined,
        apiBase.trim() || undefined
      );
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Connection test failed.' });
    } finally {
      setTesting(false);
    }
  };

  const handleSavePrompts = async () => {
    if (!prompts) return;
    setSavingPrompts(true);
    setPromptsMsg(null);
    try {
      const updated = await api.updatePrompts(prompts);
      setPrompts(updated.prompts);
      setPromptsMsg('All 7 system prompts saved to database.');
    } catch (err: any) {
      setPromptsMsg(`Error saving prompts: ${err.message}`);
    } finally {
      setSavingPrompts(false);
    }
  };

  const handleResetPrompts = async () => {
    if (
      !window.confirm(
        'Reset all 7 system prompts to factory defaults? Custom prompt edits will be overwritten.'
      )
    ) {
      return;
    }
    setSavingPrompts(true);
    setPromptsMsg(null);
    try {
      const res = await api.resetPrompts();
      setPrompts(res.prompts);
      setPromptsMsg('Prompts restored to factory defaults.');
    } catch (err: any) {
      setPromptsMsg(`Error resetting prompts: ${err.message}`);
    } finally {
      setSavingPrompts(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeFinalModel) {
      alert('Please specify a valid Model ID.');
      return;
    }
    setSaving(true);
    setSaveSuccess(false);
    try {
      const payload: any = {
        active_llm_provider: provider,
        active_llm_model: activeFinalModel,
        llm_api_base: apiBase.trim(),
        device_timezone: timezone.trim() || 'Europe/Warsaw',
        night_start_hour: Number(nightStart),
        night_end_hour: Number(nightEnd),
        chat_enter_mode: enterMode
      };
      if (apiKey.trim()) {
        payload.llm_api_key = apiKey.trim();
      }

      const updated = await api.updateSettings(payload);
      onSettingsUpdated(updated);
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
        onClose();
      }, 800);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const customModelsForProvider = modelDetails.filter((m) => m.is_custom);
  const selectedModelDetail = modelDetails.find((m) => m.id === activeFinalModel);
  const hasStoredKey =
    Boolean(currentSettings?.llm_api_key) ||
    Boolean(currentSettings?.gemini_key_set) ||
    Boolean(currentSettings?.openrouter_key_set);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="⚙️ LLM, Prompt Studio & Regional Configuration"
      maxWidth="2xl"
    >
      <form onSubmit={handleSaveSettings} className="space-y-5">
        {/* 3-Tab Navigation Header */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5">
          <button
            type="button"
            onClick={() => setActiveTab('llm')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'llm'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Key className="w-3.5 h-3.5" />
            <span>🤖 LLM Provider & Credentials</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('prompts')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'prompts'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>✍️ Prompt Studio (7)</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('preferences')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'preferences'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>🌙 Night Standby & Regional</span>
          </button>
        </div>

        {/* TAB 1: LLM Provider & Credentials */}
        {activeTab === 'llm' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  LLM Provider
                </label>
                <select
                  value={provider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {providersList.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-300">
                    Model Selection & Pricing
                  </label>
                  <button
                    type="button"
                    onClick={handleFetchLiveModels}
                    disabled={fetchingLive}
                    className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 disabled:opacity-50"
                    title="Query provider API for live available models"
                  >
                    <RefreshCw className={`w-3 h-3 ${fetchingLive ? 'animate-spin' : ''}`} />
                    <span>Fetch Live Models</span>
                  </button>
                </div>
                <select
                  value={selectedModelOption}
                  onChange={(e) => setSelectedModelOption(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                >
                  {modelDetails.map((m) => (
                    <option key={m.id} value={m.id}>
                      {formatModelLabel(m)}
                    </option>
                  ))}
                  <option value={CUSTOM_MODEL_SENTINEL}>
                    ➕ Type Custom Model ID...
                  </option>
                </select>
              </div>
            </div>

            {/* Selected Model Pricing Summary Pill */}
            {selectedModelDetail && selectedModelOption !== CUSTOM_MODEL_SENTINEL && (
              <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-900/70 border border-slate-800 text-xs">
                <span className="text-slate-400">
                  Active Model Pricing (<span className="font-mono text-slate-200">{selectedModelDetail.id}</span>):
                </span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {selectedModelDetail.pricing}
                </span>
              </div>
            )}

            {/* Inline Custom Model ID Input when sentinel is selected */}
            {selectedModelOption === CUSTOM_MODEL_SENTINEL && (
              <div className="p-3 rounded-lg bg-slate-900/60 border border-indigo-500/30 space-y-1.5">
                <label className="text-xs font-medium text-indigo-300 block">
                  Custom Model ID (LiteLLM format)
                </label>
                <Input
                  value={customTypedModel}
                  onChange={(e) => setCustomTypedModel(e.target.value)}
                  placeholder="e.g. gemini/gemini-2.5-pro-exp-03-25 or openrouter/anthropic/claude-3.7-sonnet"
                  className="text-xs font-mono"
                />
                <p className="text-[11px] text-slate-400">
                  Include the provider prefix (e.g. <code className="text-slate-300">gemini/</code>, <code className="text-slate-300">openai/</code>, <code className="text-slate-300">openrouter/</code>, <code className="text-slate-300">ollama/</code>).
                </p>
              </div>
            )}

            {liveFetchMsg && (
              <div className="text-xs px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                {liveFetchMsg}
              </div>
            )}

            {/* API Key & API Base URL */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-300">
                    API Key ({provider})
                  </label>
                  {hasStoredKey && (
                    <Badge variant="optimal" className="text-[10px]">
                      Stored in DB / Env
                    </Badge>
                  )}
                </div>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    hasStoredKey
                      ? '•••••••••••••••• (Leave blank to keep stored key)'
                      : 'Paste provider API key...'
                  }
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  API Base URL (Optional / Local / Proxy)
                </label>
                <Input
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  placeholder="Default provider endpoint (or http://localhost:11434)"
                  className="text-xs font-mono"
                />
              </div>
            </div>

            {/* Collapsible Custom Models Registry */}
            <div className="border border-slate-800 rounded-lg bg-slate-950/60 overflow-hidden">
              <button
                type="button"
                onClick={() => setShowCustomManager(!showCustomManager)}
                className="w-full flex items-center justify-between px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-900/60 transition-colors"
              >
                <span className="flex items-center gap-2">
                  {showCustomManager ? (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  <span>🛠️ Manage & Register Custom Models ({customModelsForProvider.length})</span>
                </span>
                <span className="text-[11px] font-normal text-slate-500">
                  Persist custom models to provider dropdown
                </span>
              </button>

              {showCustomManager && (
                <div className="p-3.5 border-t border-slate-800 space-y-3 bg-slate-900/30">
                  <div className="flex items-end gap-2">
                    <div className="flex-1">
                      <label className="text-[11px] text-slate-400 block mb-1">
                        Custom Model ID (e.g. gemini/gemini-2.5-flash)
                      </label>
                      <Input
                        value={newCustomModelId}
                        onChange={(e) => setNewCustomModelId(e.target.value)}
                        placeholder="provider/model-name"
                        className="text-xs font-mono"
                      />
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={handleAddCustomModel}
                      disabled={customSaving || !newCustomModelId.trim()}
                      className="h-[34px]"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Save to List</span>
                    </Button>
                  </div>

                  {customModelsForProvider.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="text-[11px] text-slate-400 font-medium">
                        Saved Custom Models for {provider}:
                      </div>
                      <div className="max-h-28 overflow-y-auto divide-y divide-slate-800/60 border border-slate-800 rounded bg-slate-950">
                        {customModelsForProvider.map((cm) => (
                          <div
                            key={cm.id}
                            className="flex items-center justify-between px-2.5 py-1.5 text-xs font-mono"
                          >
                            <span className="text-slate-200">{cm.id}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-[11px] text-slate-400">{cm.pricing}</span>
                              <button
                                type="button"
                                onClick={() => handleDeleteCustomModel(cm.id)}
                                className="text-rose-400 hover:text-rose-300 p-0.5"
                                title="Remove custom model"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Test Connection Row */}
            <div className="pt-1 flex flex-wrap items-center justify-between gap-3">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleTestConnection}
                disabled={testing}
                className="text-xs"
              >
                {testing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Key className="w-3.5 h-3.5" />
                )}
                <span>🧪 Test API Connection</span>
              </Button>

              {testResult && (
                <div
                  className={`text-xs flex items-center gap-1.5 ${
                    testResult.success ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {testResult.success ? (
                    <Check className="w-4 h-4 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0" />
                  )}
                  <span className="truncate max-w-md">{testResult.message}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: Prompt Studio */}
        {activeTab === 'prompts' && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-1.5">
              {PROMPT_LABELS.map((item) => (
                <button
                  key={String(item.key)}
                  type="button"
                  onClick={() => setActivePromptKey(item.key)}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                    activePromptKey === item.key
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {prompts ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-400">
                    {PROMPT_LABELS.find((p) => p.key === activePromptKey)?.desc}
                  </p>
                  <span className="text-[11px] font-mono text-slate-500">
                    Key: prompt_{String(activePromptKey)}
                  </span>
                </div>
                <textarea
                  rows={12}
                  value={prompts[activePromptKey] || ''}
                  onChange={(e) =>
                    setPrompts({
                      ...prompts,
                      [activePromptKey]: e.target.value
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed"
                />

                <div className="flex items-center justify-between pt-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleResetPrompts}
                    disabled={savingPrompts}
                    className="text-xs text-amber-300 hover:text-amber-200"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>🔄 Reset Prompts to Factory Defaults</span>
                  </Button>

                  <div className="flex items-center gap-3">
                    {promptsMsg && (
                      <span className="text-xs text-emerald-400">{promptsMsg}</span>
                    )}
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={handleSavePrompts}
                      disabled={savingPrompts}
                      className="text-xs"
                    >
                      {savingPrompts ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Check className="w-3.5 h-3.5" />
                      )}
                      <span>💾 Save All Prompts</span>
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading system prompts...</span>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Night Standby & Regional Settings */}
        {activeTab === 'preferences' && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Preferred Device Timezone
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <select
                  value={COMMON_TIMEZONES.includes(timezone) ? timezone : '__custom__'}
                  onChange={(e) => {
                    if (e.target.value !== '__custom__') {
                      setTimezone(e.target.value);
                    }
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {COMMON_TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                  <option value="__custom__">Custom IANA Timezone...</option>
                </select>
                <Input
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  placeholder="e.g. Europe/Warsaw"
                  className="text-xs font-mono"
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Used automatically when importing bugreports and aligning Night Standby windows.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  🌙 Night Standby Start Hour (0-23)
                </label>
                <Input
                  type="number"
                  min="0"
                  max="23"
                  value={nightStart}
                  onChange={(e) => setNightStart(Number(e.target.value))}
                  className="text-xs"
                />
                <p className="text-[11px] text-slate-500 mt-1">Default: 23 (23:00)</p>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  ☀️ Night Standby End Hour (0-23)
                </label>
                <Input
                  type="number"
                  min="0"
                  max="23"
                  value={nightEnd}
                  onChange={(e) => setNightEnd(Number(e.target.value))}
                  className="text-xs"
                />
                <p className="text-[11px] text-slate-500 mt-1">Default: 7 (07:00)</p>
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-2">
                Investigation Chat Submit Shortcut
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <label className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-800 bg-slate-950/60 cursor-pointer hover:border-slate-700">
                  <input
                    type="radio"
                    name="enterMode"
                    value="newline"
                    checked={enterMode === 'newline'}
                    onChange={() => setEnterMode('newline')}
                    className="mt-0.5 text-indigo-500 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">
                      Enter: New Line • Ctrl/⌘+Enter: Send
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Best for multiline technical questions.
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-800 bg-slate-950/60 cursor-pointer hover:border-slate-700">
                  <input
                    type="radio"
                    name="enterMode"
                    value="send"
                    checked={enterMode === 'send'}
                    onChange={() => setEnterMode('send')}
                    className="mt-0.5 text-indigo-500 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">
                      Enter: Send • Shift+Enter: New Line
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Instant messaging style for quick prompts.
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Footer Save Bar */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={saving}>
            Close
          </Button>
          <Button type="submit" variant="primary" size="sm" disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Saving...</span>
              </>
            ) : saveSuccess ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Saved & Applied!</span>
              </>
            ) : (
              <span>💾 Save & Apply Configuration</span>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
