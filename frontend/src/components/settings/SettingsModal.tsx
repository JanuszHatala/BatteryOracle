import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import { api } from '../../api/client';
import { Settings, ModelsResponse } from '../../types/api';
import { Sliders, Key, Globe, Moon, Check, AlertCircle, Loader2 } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSettings: Settings | null;
  onSettingsUpdated: (newSettings: Settings) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentSettings,
  onSettingsUpdated
}) => {
  const [activeTab, setActiveTab] = useState<'llm' | 'preferences'>('llm');
  const [geminiKey, setGeminiKey] = useState('');
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [provider, setProvider] = useState('Google Gemini');
  const [model, setModel] = useState('gemini-3.8-flash');
  const [modelsList, setModelsList] = useState<string[]>([]);
  const [timezone, setTimezone] = useState('UTC');
  const [nightStart, setNightStart] = useState(23);
  const [nightEnd, setNightEnd] = useState(7);
  const [enterMode, setEnterMode] = useState<'newline' | 'send'>('newline');

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (currentSettings) {
      setProvider(currentSettings.active_llm_provider || 'Google Gemini');
      setModel(currentSettings.active_llm_model || 'gemini-3.8-flash');
      setTimezone(currentSettings.device_timezone || 'UTC');
      setNightStart(currentSettings.night_start_hour ?? 23);
      setNightEnd(currentSettings.night_end_hour ?? 7);
      setEnterMode(currentSettings.chat_enter_mode || 'newline');
    }
  }, [currentSettings, isOpen]);

  useEffect(() => {
    if (isOpen) {
      api.getModels(provider)
        .then((res: ModelsResponse) => {
          setModelsList(res.models);
          if (!res.models.includes(model) && res.models.length > 0) {
            setModel(res.default_model || res.models[0]);
          }
        })
        .catch(console.error);
    }
  }, [provider, isOpen]);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConnection(model, provider, provider === 'Google Gemini' ? geminiKey : openrouterKey);
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Connection test failed.' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      const payload: any = {
        active_llm_provider: provider,
        active_llm_model: model,
        device_timezone: timezone,
        night_start_hour: Number(nightStart),
        night_end_hour: Number(nightEnd),
        chat_enter_mode: enterMode
      };
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();
      if (openrouterKey.trim()) payload.openrouter_api_key = openrouterKey.trim();

      const updated = await api.updateSettings(payload);
      onSettingsUpdated(updated);
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
        onClose();
      }, 1000);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Platform Settings & Preferences" maxWidth="xl">
      <form onSubmit={handleSave} className="space-y-6">
        {/* Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
          <button
            type="button"
            onClick={() => setActiveTab('llm')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'llm'
                ? 'bg-slate-800 text-slate-100 border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Key className="w-3.5 h-3.5" />
            <span>LLM Configuration</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('preferences')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'preferences'
                ? 'bg-slate-800 text-slate-100 border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Telemetry & Shortcuts</span>
          </button>
        </div>

        {/* Tab 1: LLM Config */}
        {activeTab === 'llm' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">AI Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="Google Gemini">Google Gemini</option>
                  <option value="OpenRouter">OpenRouter</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Active Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                >
                  {modelsList.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-300">Google Gemini API Key</label>
                  {currentSettings?.gemini_key_set && (
                    <Badge variant="optimal" className="text-[10px]">Configured</Badge>
                  )}
                </div>
                <Input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder={currentSettings?.gemini_key_set ? "•••••••••••••••• (Leave blank to keep)" : "AIzaSy..."}
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-300">OpenRouter API Key</label>
                  {currentSettings?.openrouter_key_set && (
                    <Badge variant="optimal" className="text-[10px]">Configured</Badge>
                  )}
                </div>
                <Input
                  type="password"
                  value={openrouterKey}
                  onChange={(e) => setOpenrouterKey(e.target.value)}
                  placeholder={currentSettings?.openrouter_key_set ? "•••••••••••••••• (Leave blank to keep)" : "sk-or-v1-..."}
                  className="text-xs font-mono"
                />
              </div>
            </div>

            {/* Test Connection Button */}
            <div className="pt-2 flex items-center justify-between">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleTestConnection}
                disabled={testing}
                className="text-xs"
              >
                {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Key className="w-3.5 h-3.5" />}
                <span>Test API Connection</span>
              </Button>

              {testResult && (
                <div className={`text-xs flex items-center gap-1.5 ${testResult.success ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {testResult.success ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                  <span>{testResult.message}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Preferences */}
        {activeTab === 'preferences' && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Device Timezone</label>
              <Input
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                placeholder="e.g. Europe/Warsaw or UTC"
                className="text-xs"
              />
              <p className="text-[11px] text-slate-500 mt-1">Used to parse bugreport logcat and batterystats clock transitions.</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Night Standby Start Hour</label>
                <Input
                  type="number"
                  min="0"
                  max="23"
                  value={nightStart}
                  onChange={(e) => setNightStart(Number(e.target.value))}
                  className="text-xs"
                />
                <p className="text-[11px] text-slate-500 mt-1">Default 23 (11:00 PM).</p>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Night Standby End Hour</label>
                <Input
                  type="number"
                  min="0"
                  max="23"
                  value={nightEnd}
                  onChange={(e) => setNightEnd(Number(e.target.value))}
                  className="text-xs"
                />
                <p className="text-[11px] text-slate-500 mt-1">Default 7 (07:00 AM).</p>
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-2">Investigation Chat Submit Shortcut</label>
              <div className="space-y-2">
                <label className="flex items-center gap-3 p-3 rounded-lg border border-slate-800 bg-slate-950/60 cursor-pointer hover:border-slate-700">
                  <input
                    type="radio"
                    name="enterMode"
                    value="newline"
                    checked={enterMode === 'newline'}
                    onChange={() => setEnterMode('newline')}
                    className="text-emerald-500 focus:ring-emerald-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">Enter: New Line • Ctrl+Enter / ⌘+Enter: Send (Default)</span>
                    <span className="text-[11px] text-slate-400">Best for multiline diagnostic questions without accidental submits.</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-lg border border-slate-800 bg-slate-950/60 cursor-pointer hover:border-slate-700">
                  <input
                    type="radio"
                    name="enterMode"
                    value="send"
                    checked={enterMode === 'send'}
                    onChange={() => setEnterMode('send')}
                    className="text-emerald-500 focus:ring-emerald-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">Enter: Send • Shift+Enter: New Line</span>
                    <span className="text-[11px] text-slate-400">Instant messaging style for quick questions.</span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={saving}>
            Cancel
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
                <span>Saved!</span>
              </>
            ) : (
              <span>Save Settings</span>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
