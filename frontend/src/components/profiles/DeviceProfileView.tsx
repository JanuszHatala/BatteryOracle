import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import {
  DeviceProfile,
  DeviceProfileDetail,
  ProfileComparisonResponse,
  WifiRouter
} from '../../types/api';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import { useDialog } from '../ui/DialogContext';
import { ChatWorkspace } from '../chat/ChatWorkspace';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Shield,
  Wifi,
  MessageSquare,
  Upload,
  Terminal,
  Sparkles,
  Trash2,
  Edit3,
  Check,
  AlertTriangle,
  Search,
  Loader2,
  Download,
  Copy,
  Star,
  Info,
  X
} from 'lucide-react';

const ADB_CAPTURE_SCRIPT = `adb get-state 1>/dev/null 2>&1 && {
  FILENAME="device_profile_$(date +%Y%m%d_%H%M%S).txt"
  echo "Connected. Capturing configuration to $FILENAME..."
  adb shell '
echo "=== DEVICE_HEADER ===";
echo "model=$(getprop ro.product.model)";
echo "manufacturer=$(getprop ro.product.manufacturer)";
echo "android_version=$(getprop ro.build.version.release)";
echo "sdk=$(getprop ro.build.version.sdk)";
echo "build_id=$(getprop ro.build.display.id)";
echo "=== SETTINGS_GLOBAL ==="; settings list global;
echo "=== SETTINGS_SECURE ==="; settings list secure;
echo "=== SETTINGS_SYSTEM ==="; settings list system;
echo "=== DEVICEIDLE ==="; dumpsys deviceidle;
echo "=== APPOPS_RUN_IN_BG ==="; cmd appops query-op RUN_IN_BACKGROUND allow; cmd appops query-op RUN_IN_BACKGROUND ignore;
echo "=== APPOPS_RUN_ANY_IN_BG ==="; cmd appops query-op RUN_ANY_IN_BACKGROUND allow; cmd appops query-op RUN_ANY_IN_BACKGROUND ignore;
echo "=== APPOPS_WAKE_LOCK ==="; cmd appops query-op WAKE_LOCK allow; cmd appops query-op WAKE_LOCK ignore;
echo "=== POWER_MANAGER ==="; dumpsys power;
echo "=== WIFI_STATUS ==="; cmd wifi status;
' > "$FILENAME"
  echo "Done! Snapshot saved to $FILENAME"
} || echo "Error: No Android device detected via ADB. Ensure USB debugging is enabled."`;

export const DeviceProfileView: React.FC = () => {
  const { showError, confirm } = useDialog();
  const [profiles, setProfiles] = useState<DeviceProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [activeProfile, setActiveProfile] = useState<DeviceProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // Mode: 'single' | 'compare'
  const [viewMode, setViewMode] = useState<'single' | 'compare'>('single');
  const [activeSubTab, setActiveSubTab] = useState<'audit' | 'wifi' | 'chat'>('audit');

  // ADB instructions & Upload modal
  const [showAdbScript, setShowAdbScript] = useState(false);
  const [copiedAdb, setCopiedAdb] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadMode, setUploadMode] = useState<'new' | 'overwrite'>('new');
  const [uploadLabel, setUploadLabel] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadFileError, setUploadFileError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // Prompt banner to run audit after uploading
  const [justUploadedProfileId, setJustUploadedProfileId] = useState<number | null>(null);
  const [settingActiveProfileId, setSettingActiveProfileId] = useState<number | null>(null);

  // Rename state
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameText, setRenameText] = useState('');

  // AI Audit state
  const [auditing, setAuditing] = useState(false);

  // AppOps & Settings Explorer state
  const [appOpsTab, setAppOpsTab] = useState<'ignore' | 'unrestricted' | 'foreground' | 'allow'>('ignore');
  const [settingsNamespace, setSettingsNamespace] = useState<'all' | 'global' | 'secure' | 'system'>('all');
  const [settingsSearch, setSettingsSearch] = useState('');

  // Compare Profiles state
  const [compareBaselineId, setCompareBaselineId] = useState<number | null>(null);
  const [compareTargetId, setCompareTargetId] = useState<number | null>(null);
  const [comparisonData, setComparisonData] = useState<ProfileComparisonResponse | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareAuditing, setCompareAuditing] = useState(false);
  const [compareAuditMarkdown, setCompareAuditMarkdown] = useState<string | null>(null);

  // WiFi Routers state
  const [routers, setRouters] = useState<WifiRouter[]>([]);
  const [selectedRouterId, setSelectedRouterId] = useState<number | null>(null);
  const [newRouterBrand, setNewRouterBrand] = useState('');
  const [newRouterModel, setNewRouterModel] = useState('');
  const [discoveringRouter, setDiscoveringRouter] = useState(false);
  const [editingRouter, setEditingRouter] = useState<Partial<WifiRouter>>({});
  const [savingRouter, setSavingRouter] = useState(false);

  const loadProfilesAndRouters = async (preferredId?: number) => {
    setLoading(true);
    try {
      const [profs, rtrs] = await Promise.all([
        api.getProfiles(),
        api.getRouters()
      ]);
      setProfiles(profs);
      setRouters(rtrs);

      if (profs.length > 0) {
        const targetId = preferredId ?? selectedProfileId ?? profs[0].id;
        setSelectedProfileId(targetId);
        if (profs.length >= 2 && !compareBaselineId && !compareTargetId) {
          setCompareBaselineId(profs[1].id);
          setCompareTargetId(profs[0].id);
        }
      } else {
        setSelectedProfileId(null);
        setActiveProfile(null);
      }

      if (rtrs.length > 0 && !selectedRouterId) {
        const activeRtr = rtrs.find((r) => r.is_active === 1) || rtrs[0];
        setSelectedRouterId(activeRtr.id);
        setEditingRouter(activeRtr);
      }
    } catch (err) {
      console.error('Failed to load profiles/routers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfilesAndRouters();
  }, []);

  useEffect(() => {
    if (selectedProfileId) {
      api
        .getProfile(selectedProfileId)
        .then((p) => {
          setActiveProfile(p);
          setRenameText(p.profile_name || p.device_model || `Profile #${p.id}`);
        })
        .catch(console.error);
    }
  }, [selectedProfileId]);

  useEffect(() => {
    if (viewMode === 'compare' && compareBaselineId && compareTargetId && compareBaselineId !== compareTargetId) {
      setComparing(true);
      setCompareAuditMarkdown(null);
      api
        .compareProfiles(compareBaselineId, compareTargetId)
        .then((res) => {
          setComparisonData(res);
          if (res.ai_analysis) setCompareAuditMarkdown(res.ai_analysis);
        })
        .catch(console.error)
        .finally(() => setComparing(false));
    }
  }, [viewMode, compareBaselineId, compareTargetId]);

  const handleFileChange = (file: File | null) => {
    setUploadFile(file);
    setUploadFileError(null);
    if (file) {
      if (file.size < 50) {
        setUploadFileError('The selected file is too small (< 50 bytes) and appears empty or corrupted.');
      } else if (!file.name.toLowerCase().endsWith('.txt') && !file.name.toLowerCase().endsWith('.log')) {
        setUploadFileError('Device profile snapshot should be a .txt or .log file.');
      }
    }
  };

  const handleUploadProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    if (uploadFile.size < 50) {
      setUploadFileError('File size is under 50 bytes. Please provide a valid device profile dump.');
      return;
    }
    setUploading(true);
    try {
      const targetOverwriteId =
        uploadMode === 'overwrite' && selectedProfileId ? selectedProfileId : undefined;
      const saved = await api.uploadProfile(
        uploadFile,
        uploadLabel.trim() || undefined,
        targetOverwriteId
      );
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadLabel('');
      setUploadFileError(null);
      await loadProfilesAndRouters(saved.id);
      setActiveProfile(saved);
      setSelectedProfileId(saved.id);
      setJustUploadedProfileId(saved.id);
    } catch (err: any) {
      showError(err, 'Uploading Device Profile');
    } finally {
      setUploading(false);
    }
  };

  const handleSetActiveContext = async (profileId: number) => {
    setSettingActiveProfileId(profileId);
    try {
      await api.setActiveProfile(profileId);
      await loadProfilesAndRouters(profileId);
      if (selectedProfileId === profileId && activeProfile) {
        setActiveProfile({ ...activeProfile, is_active_context: true });
      }
    } catch (err: any) {
      showError(err, 'Setting Default Context Profile');
    } finally {
      setSettingActiveProfileId(null);
    }
  };

  const handleRenameProfile = async () => {
    if (!activeProfile || !renameText.trim()) return;
    try {
      const updated = await api.renameProfile(activeProfile.id, renameText.trim());
      setActiveProfile(updated);
      setIsRenaming(false);
      loadProfilesAndRouters(updated.id);
    } catch (err: any) {
      showError(err, 'Renaming Device Profile');
    }
  };

  const handleDeleteProfile = async () => {
    if (!activeProfile) return;
    const ok = await confirm({
      title: 'Delete Device Profile',
      message: `Are you sure you want to permanently delete device profile "${activeProfile.profile_name}"?`,
      confirmLabel: 'Delete Profile',
      variant: 'danger'
    });
    if (!ok) return;

    try {
      await api.deleteProfile(activeProfile.id);
      await loadProfilesAndRouters();
    } catch (err: any) {
      showError(err, 'Deleting Device Profile');
    }
  };

  const handleGenerateAudit = async () => {
    if (!activeProfile) return;
    setAuditing(true);
    try {
      const updated = await api.auditProfile(activeProfile.id);
      setActiveProfile(updated);
    } catch (err: any) {
      showError(err, 'Running AI Device Profile Audit');
    } finally {
      setAuditing(false);
    }
  };

  const handleExportAuditMarkdown = () => {
    if (!activeProfile?.analysis_text) return;
    const blob = new Blob([activeProfile.analysis_text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `device_audit_${activeProfile.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleGenerateCompareAudit = async () => {
    if (!compareBaselineId || !compareTargetId) return;
    setCompareAuditing(true);
    try {
      const res = await api.auditProfileComparison(compareBaselineId, compareTargetId);
      setCompareAuditMarkdown(res.ai_analysis);
    } catch (err: any) {
      showError(err, 'Running Profile Comparison AI Audit');
    } finally {
      setCompareAuditing(false);
    }
  };

  // Router handlers
  const handleDiscoverRouter = async (autoDiscover: boolean) => {
    if (!newRouterBrand.trim() && !newRouterModel.trim()) return;
    setDiscoveringRouter(true);
    try {
      const brand = newRouterBrand.trim() || 'Generic';
      const model = newRouterModel.trim() || 'Router';
      let specs: Record<string, any> = {};
      if (autoDiscover) {
        const disc = await api.discoverRouterSpecs(brand, model);
        specs = disc.specs || {};
      }
      const created = await api.createRouter({
        router_name: `${brand} ${model}`.trim(),
        brand,
        model,
        specs_json: specs,
        location_tag: 'Home',
        is_active: 1,
        notes: ''
      });
      setNewRouterBrand('');
      setNewRouterModel('');
      const updatedRouters = await api.getRouters();
      setRouters(updatedRouters);
      setSelectedRouterId(created.id);
      setEditingRouter(created);
    } catch (err: any) {
      showError(err, 'Creating Wi-Fi Router Profile');
    } finally {
      setDiscoveringRouter(false);
    }
  };

  const handleSaveRouterChanges = async () => {
    if (!selectedRouterId) return;
    setSavingRouter(true);
    try {
      const updated = await api.updateRouter(selectedRouterId, editingRouter);
      const updatedList = await api.getRouters();
      setRouters(updatedList);
      setEditingRouter(updated);
    } catch (err: any) {
      showError(err, 'Updating Wi-Fi Router Profile');
    } finally {
      setSavingRouter(false);
    }
  };

  const handleDeleteRouter = async () => {
    if (!selectedRouterId) return;
    const ok = await confirm({
      title: 'Delete Wi-Fi Router Profile',
      message: 'Are you sure you want to delete this Wi-Fi router profile?',
      confirmLabel: 'Delete Router',
      variant: 'danger'
    });
    if (!ok) return;

    try {
      await api.deleteRouter(selectedRouterId);
      const updatedList = await api.getRouters();
      setRouters(updatedList);
      if (updatedList.length > 0) {
        setSelectedRouterId(updatedList[0].id);
        setEditingRouter(updatedList[0]);
      } else {
        setSelectedRouterId(null);
        setEditingRouter({});
      }
    } catch (err: any) {
      showError(err, 'Deleting Wi-Fi Router Profile');
    }
  };

  const profileData = activeProfile?.parsed_data || {};
  const kpis = profileData.kpis || {};
  const risks: any[] = profileData.risks || [];
  const highlights = profileData.highlights || {};
  const whitelist = profileData.doze_whitelist || { user_apps: [], system_apps: [] };
  const appops = profileData.appops_summary || { ignore: [], unrestricted: [], foreground: [], allow: [] };
  const settingsMap = profileData.settings || { global: {}, secure: {}, system: {} };

  // Build filtered settings rows
  const filteredSettingsRows = React.useMemo(() => {
    const rows: { namespace: string; key: string; value: string }[] = [];
    const namespaces =
      settingsNamespace === 'all' ? ['global', 'secure', 'system'] : [settingsNamespace];
    const q = settingsSearch.trim().toLowerCase();

    for (const ns of namespaces) {
      const dict = settingsMap[ns] || {};
      for (const [k, v] of Object.entries(dict)) {
        const valStr = String(v ?? '');
        if (!q || k.toLowerCase().includes(q) || valStr.toLowerCase().includes(q)) {
          rows.push({ namespace: ns, key: k, value: valStr });
        }
      }
    }
    return rows.slice(0, 300);
  }, [settingsMap, settingsNamespace, settingsSearch]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Loading Device Profiles & Router Environment...</span>
      </div>
    );
  }

  const editingSpecs = editingRouter.specs_json || {};

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Top Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-400" />
            <span>📱 Device Profile & Configuration Audit</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Inspect Android system settings, Doze parameters, AppOps restrictions, and WiFi router DTIM/TWT environment.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button
              type="button"
              onClick={() => setViewMode('single')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                viewMode === 'single'
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🔍 Single Profile Audit
            </button>
            <button
              type="button"
              onClick={() => setViewMode('compare')}
              disabled={profiles.length < 2}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors disabled:opacity-40 ${
                viewMode === 'compare'
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ⚖️ Compare Profiles ({profiles.length})
            </button>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowAdbScript(!showAdbScript)}
            className="text-xs"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>ADB Capture Command</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowUploadModal(true)}
            className="text-xs"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Profile (.txt)</span>
          </Button>
        </div>
      </div>

      {/* Collapsible ADB Script Box */}
      {showAdbScript && (
        <Card className="p-4 border-indigo-500/30 bg-slate-900/90 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-300">
              📋 Run this command with your Android phone connected via USB Debugging:
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(ADB_CAPTURE_SCRIPT);
                setCopiedAdb(true);
                setTimeout(() => setCopiedAdb(false), 2000);
              }}
              className="text-xs"
            >
              {copiedAdb ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedAdb ? 'Copied!' : 'Copy Command'}</span>
            </Button>
          </div>
          <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto whitespace-pre">
            {ADB_CAPTURE_SCRIPT}
          </pre>
        </Card>
      )}

      {/* Upload Profile Modal Dialog */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <Card className="w-full max-w-lg p-6 border-indigo-500/40 bg-slate-900 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-slate-100 font-semibold text-sm">
                <Upload className="w-4 h-4 text-indigo-400" />
                <span>Upload Device Profile Snapshot</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadFile(null);
                  setUploadFileError(null);
                }}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUploadProfile} className="space-y-4">
              <div className="flex items-center gap-4 text-xs bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                  <input
                    type="radio"
                    checked={uploadMode === 'new'}
                    onChange={() => setUploadMode('new')}
                  />
                  <span>➕ Create New Profile</span>
                </label>
                {selectedProfileId && (
                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-300">
                    <input
                      type="radio"
                      checked={uploadMode === 'overwrite'}
                      onChange={() => setUploadMode('overwrite')}
                    />
                    <span>🔄 Overwrite Selected (#{selectedProfileId})</span>
                  </label>
                )}
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">
                  Profile Label (Optional)
                </label>
                <Input
                  value={uploadLabel}
                  onChange={(e) => setUploadLabel(e.target.value)}
                  placeholder="e.g. Pixel 9 Pro - After 5G & AOD Tweak"
                  className="text-xs"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">
                  Select Snapshot File (`device_profile_*.txt` or `.log`)
                </label>
                <input
                  type="file"
                  accept=".txt,.log"
                  onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-300 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />
                {uploadFile && (
                  <div className="mt-1.5 text-[11px] text-slate-400">
                    Selected: <strong className="text-slate-200">{uploadFile.name}</strong> ({(uploadFile.size / 1024).toFixed(1)} KB)
                  </div>
                )}
                {uploadFileError && (
                  <div className="mt-2 text-xs text-rose-400 bg-rose-950/40 border border-rose-800/60 rounded p-2">
                    {uploadFileError}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowUploadModal(false);
                    setUploadFile(null);
                    setUploadFileError(null);
                  }}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!uploadFile || !!uploadFileError || uploading}
                  className="text-xs"
                >
                  {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  <span>{uploading ? 'Validating & Parsing...' : 'Parse & Save Profile'}</span>
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Just Uploaded Profile: Prompt to Run AI Audit */}
      {justUploadedProfileId && activeProfile && activeProfile.id === justUploadedProfileId && !activeProfile.analysis_text && (
        <Card className="p-4 bg-indigo-950/40 border-indigo-500/50 flex flex-wrap items-center justify-between gap-3 animate-in fade-in duration-200">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-5 h-5 text-indigo-400 shrink-0" />
            <div>
              <div className="text-xs font-bold text-indigo-200">
                Device profile uploaded successfully: #{activeProfile.id} ({activeProfile.profile_name})
              </div>
              <div className="text-[11px] text-indigo-300/80">
                Would you like to run the automated AI Configuration & Doze Audit now?
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={async () => {
                setJustUploadedProfileId(null);
                await handleGenerateAudit();
              }}
              disabled={auditing}
              className="text-xs"
            >
              {auditing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              <span>Run AI Audit Now</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setJustUploadedProfileId(null)}
              className="text-xs text-slate-400"
            >
              Dismiss
            </Button>
          </div>
        </Card>
      )}

      {/* COMPARE PROFILES MODE */}
      {viewMode === 'compare' && (
        <div className="space-y-6">
          <Card className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">
                  Baseline Profile (Before)
                </label>
                <select
                  value={compareBaselineId || ''}
                  onChange={(e) => setCompareBaselineId(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                >
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      #{p.id} - {p.profile_name || p.device_model} ({p.created_at})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">
                  Target Profile (After)
                </label>
                <select
                  value={compareTargetId || ''}
                  onChange={(e) => setCompareTargetId(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                >
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      #{p.id} - {p.profile_name || p.device_model} ({p.created_at})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </Card>

          {comparing ? (
            <div className="py-12 text-center text-xs text-slate-400">
              Computing configuration diff...
            </div>
          ) : comparisonData ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Settings Changed</div>
                  <div className="text-2xl font-bold text-indigo-400 mt-1">
                    {comparisonData.diff.summary?.total_settings_changed ?? 0}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Whitelist Added</div>
                  <div className="text-2xl font-bold text-amber-400 mt-1">
                    +{comparisonData.diff.summary?.whitelist_added_count ?? 0}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Whitelist Removed</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    -{comparisonData.diff.summary?.whitelist_removed_count ?? 0}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">AppOps Changed</div>
                  <div className="text-2xl font-bold text-sky-400 mt-1">
                    {comparisonData.diff.summary?.appops_changed_count ?? 0}
                  </div>
                </Card>
              </div>

              {/* AI Comparison Analysis */}
              <Card className="p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200">
                      🤖 AI Configuration Diff Analysis
                    </h3>
                    <p className="text-xs text-slate-400">
                      Evaluate how the configuration changes between Baseline and Target impact standby battery drain.
                    </p>
                  </div>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleGenerateCompareAudit}
                    disabled={compareAuditing}
                    className="text-xs"
                  >
                    {compareAuditing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5" />
                    )}
                    <span>Generate AI Diff Audit</span>
                  </Button>
                </div>
                {compareAuditMarkdown && (
                  <div className="prose prose-invert prose-sm max-w-none border-t border-slate-800 pt-4">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {compareAuditMarkdown}
                    </ReactMarkdown>
                  </div>
                )}
              </Card>

              {/* Settings Diff Table */}
              <Card className="p-5 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200">
                      Modified System Settings (`global` / `secure` / `system`)
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Highlights Android system key differences between the Baseline and Target snapshots.
                    </p>
                  </div>
                  <div className="text-[11px] text-slate-400 bg-slate-950 border border-slate-800 rounded px-2.5 py-1">
                    <span className="text-rose-400 font-semibold">Before</span> vs <span className="text-emerald-400 font-semibold">After</span>
                  </div>
                </div>

                {/* Explanation Callout for Modified System Settings */}
                <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-3 text-xs text-slate-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-indigo-300">
                    <Info className="w-3.5 h-3.5" />
                    <span>What is this section and how is it used?</span>
                  </div>
                  <p className="text-slate-400 leading-relaxed text-[11px]">
                    Android maintains three system databases accessed via `settings list [namespace]`:
                    <strong className="text-slate-300"> global</strong> (device-wide flags like Wi-Fi scan throttling, 5G mode, BLE scan),
                    <strong className="text-slate-300"> secure</strong> (security and privacy flags like location mode, wake gestures, AOD), and
                    <strong className="text-slate-300"> system</strong> (per-user display timeout, screen brightness, haptics).
                    This table reveals exact config changes between snapshots, explaining why battery drain rates shifted after an OS update or tweak.
                  </p>
                </div>

                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="py-2 px-3">Namespace</th>
                        <th className="py-2 px-3">Setting Key</th>
                        <th className="py-2 px-3">Before</th>
                        <th className="py-2 px-3">After</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {['global', 'secure', 'system'].flatMap((ns) =>
                        (comparisonData.diff.settings_changed?.[ns] || []).map((row: any, i: number) => (
                          <tr key={`${ns}-${i}`} className="hover:bg-slate-900/50">
                            <td className="py-1.5 px-3 text-indigo-400">{ns}</td>
                            <td className="py-1.5 px-3 text-slate-200">{row.key}</td>
                            <td className="py-1.5 px-3 text-rose-400 break-all">{String(row.before)}</td>
                            <td className="py-1.5 px-3 text-emerald-400 break-all">{String(row.after)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          ) : null}
        </div>
      )}

      {/* SINGLE PROFILE AUDIT MODE */}
      {viewMode === 'single' && (
        <>
          {profiles.length === 0 ? (
            <Card className="p-10 text-center space-y-3">
              <Shield className="w-10 h-10 text-slate-500 mx-auto" />
              <h3 className="text-base font-semibold text-slate-200">
                No Device Profiles Uploaded Yet
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Click "ADB Capture Command" above to dump your phone's live configuration and upload `device_profile.txt`.
              </p>
            </Card>
          ) : (
            <div className="space-y-6">
              {/* Profile Selector & Context Indicator Bar */}
              <Card className="p-4 flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-3 flex-1">
                  <select
                    value={selectedProfileId || ''}
                    onChange={(e) => setSelectedProfileId(Number(e.target.value))}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200 min-w-[280px]"
                  >
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.is_active_context ? '⭐ ' : ''}#{p.id} • {p.profile_name} ({p.device_model} / {p.os_build}) {p.is_active_context ? '[Default Context]' : ''}
                      </option>
                    ))}
                  </select>

                  {/* Active Context Profile Badge & Switcher */}
                  {activeProfile?.is_active_context ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      <span>Default Global Context Profile</span>
                    </span>
                  ) : activeProfile ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleSetActiveContext(activeProfile.id)}
                      disabled={settingActiveProfileId === activeProfile.id}
                      className="text-xs"
                      title="Set this profile as background device context for bugreport AI diagnostics and chat sessions"
                    >
                      {settingActiveProfileId === activeProfile.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Star className="w-3.5 h-3.5" />
                      )}
                      <span>Set as Default Context</span>
                    </Button>
                  ) : null}

                  {isRenaming ? (
                    <div className="flex items-center gap-1.5">
                      <Input
                        value={renameText}
                        onChange={(e) => setRenameText(e.target.value)}
                        className="text-xs h-8 w-56"
                      />
                      <Button variant="primary" size="sm" onClick={handleRenameProfile} className="text-xs">
                        Save
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setIsRenaming(false)} className="text-xs">
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsRenaming(true)}
                      className="text-xs"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Rename</span>
                    </Button>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {activeProfile && (
                    <Badge variant="scope">
                      {activeProfile.device_model} • {activeProfile.os_build}
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDeleteProfile}
                    className="text-xs text-rose-400 hover:text-rose-300"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </Button>
                </div>
              </Card>

              {/* 5 KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Standby Risks Found</div>
                  <div className={`text-2xl font-bold mt-1 ${(kpis.risk_count || 0) > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {kpis.risk_count ?? risks.length}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Doze Whitelisted (User)</div>
                  <div className="text-2xl font-bold text-indigo-400 mt-1">
                    {kpis.whitelisted_user_apps ?? whitelist.user_apps?.length ?? 0}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Background Restricted</div>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {kpis.restricted_apps_count ?? appops.ignore?.length ?? 0}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Unrestricted (RUN_ANY)</div>
                  <div className="text-2xl font-bold text-sky-400 mt-1">
                    {kpis.unrestricted_apps_count ?? appops.unrestricted?.length ?? 0}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-xs text-slate-400">Settings Keys Captured</div>
                  <div className="text-2xl font-bold text-slate-200 mt-1">
                    {kpis.total_settings_keys ?? 0}
                  </div>
                </Card>
              </div>

              {/* 3 Sub-Tabs Navigation */}
              <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                <button
                  type="button"
                  onClick={() => setActiveSubTab('audit')}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                    activeSubTab === 'audit'
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>🛡️ Configuration Audit & System Environment</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSubTab('wifi')}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                    activeSubTab === 'wifi'
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Wifi className="w-3.5 h-3.5" />
                  <span>📡 WiFi Router Environment ({routers.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSubTab('chat')}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                    activeSubTab === 'chat'
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>💬 Configuration & Doze Consultation Chat</span>
                </button>
              </div>

              {/* SUB-TAB 1: CONFIGURATION AUDIT & SYSTEM ENVIRONMENT */}
              {activeSubTab === 'audit' && activeProfile && (
                <div className="space-y-6">
                  {/* AI Audit Card */}
                  <Card className="p-5 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-200">
                          🤖 AI Configuration & Doze Audit
                        </h3>
                        <p className="text-xs text-slate-400">
                          Cross-references system settings, Doze exemptions, and active WiFi router specs against latest bugreport telemetry.
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {activeProfile.analysis_text && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={handleExportAuditMarkdown}
                            className="text-xs"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>Export .md</span>
                          </Button>
                        )}
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={handleGenerateAudit}
                          disabled={auditing}
                          className="text-xs"
                        >
                          {auditing ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Sparkles className="w-3.5 h-3.5" />
                          )}
                          <span>
                            {activeProfile.analysis_text
                              ? '🔄 Re-Run AI Configuration Audit'
                              : '✨ Generate AI Configuration Audit'}
                          </span>
                        </Button>
                      </div>
                    </div>

                    {activeProfile.analysis_text ? (
                      <div className="prose prose-invert prose-sm max-w-none border-t border-slate-800 pt-4">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {activeProfile.analysis_text}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-500 py-4 text-center border-t border-slate-800/60">
                        Click "Generate AI Configuration Audit" to evaluate your device setup and generate safe ADB tuning commands.
                      </div>
                    )}
                  </Card>

                  {/* Standby Risk Flags */}
                  <Card className="p-5 space-y-3">
                    <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      <span>⚠️ Automated Standby Power Risk Flags ({risks.length})</span>
                    </h3>
                    {risks.length === 0 ? (
                      <p className="text-xs text-emerald-400">
                        No obvious high-drain configuration risks detected in system settings!
                      </p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {risks.map((r, idx) => (
                          <div
                            key={idx}
                            className="p-3.5 rounded-lg border border-slate-800 bg-slate-950/60 space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-amber-300 font-mono">
                                [{r.severity}] {r.key}
                              </span>
                              <span className="text-[11px] font-mono text-slate-400">
                                Current: <strong className="text-rose-400">{String(r.current_value)}</strong> → Rec: <strong className="text-emerald-400">{String(r.recommended_value)}</strong>
                              </span>
                            </div>
                            <p className="text-xs text-slate-300">{r.impact}</p>
                            {r.fix_cmd && (
                              <pre className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-indigo-300 overflow-x-auto">
                                {r.fix_cmd}
                              </pre>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  {/* 5 Radio, Display & Doze Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { title: '📡 Mobile Radio & 5G', data: highlights.network_radio || {} },
                      { title: '📶 WiFi & Scan Throttling', data: highlights.wifi_scanning || {} },
                      { title: '🔆 Display, AOD & Wake Gestures', data: highlights.display_aod || {} },
                      { title: '📍 Location, BLE & UWB', data: highlights.location_ble || {} },
                      { title: '💤 Doze & App Standby', data: highlights.doze_power || {} }
                    ].map((section) => (
                      <Card key={section.title} className="p-4 space-y-2">
                        <h4 className="text-xs font-bold text-slate-200 border-b border-slate-800 pb-1.5">
                          {section.title}
                        </h4>
                        <div className="space-y-1 max-h-48 overflow-y-auto text-xs font-mono">
                          {Object.entries(section.data).map(([k, v]) => (
                            <div key={k} className="flex items-center justify-between gap-2 py-0.5">
                              <span className="text-slate-400 truncate" title={k}>{k}</span>
                              <span className="text-slate-200 font-semibold shrink-0">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </Card>
                    ))}
                  </div>

                  {/* Doze Whitelist & AppOps Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Card className="p-5 space-y-3">
                      <h3 className="text-sm font-semibold text-slate-200">
                        🛡️ Doze Battery Optimization Whitelist
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div className="text-xs font-medium text-amber-300 mb-1.5">
                            User / 3rd-Party Exempt ({whitelist.user_apps?.length || 0})
                          </div>
                          <div className="max-h-52 overflow-y-auto bg-slate-950 border border-slate-800 rounded p-2 text-xs font-mono space-y-1">
                            {(whitelist.user_apps || []).map((pkg: string) => (
                              <div key={pkg} className="text-slate-300 truncate">{pkg}</div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-medium text-slate-400 mb-1.5">
                            System Exempt ({whitelist.system_apps?.length || 0})
                          </div>
                          <div className="max-h-52 overflow-y-auto bg-slate-950 border border-slate-800 rounded p-2 text-xs font-mono space-y-1">
                            {(whitelist.system_apps || []).map((pkg: string) => (
                              <div key={pkg} className="text-slate-400 truncate">{pkg}</div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </Card>

                    <Card className="p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-slate-200">
                          ⚙️ AppOps Background Restrictions
                        </h3>
                        <div className="flex gap-1">
                          {(
                            [
                              { k: 'ignore', label: `🚫 Restricted (${appops.ignore?.length || 0})` },
                              { k: 'unrestricted', label: `⚡ Unrestricted (${appops.unrestricted?.length || 0})` },
                              { k: 'foreground', label: `🏃 FG Only (${appops.foreground?.length || 0})` },
                              { k: 'allow', label: `✅ Default (${appops.allow?.length || 0})` }
                            ] as const
                          ).map((t) => (
                            <button
                              key={t.k}
                              type="button"
                              onClick={() => setAppOpsTab(t.k)}
                              className={`px-2 py-1 rounded text-[11px] font-medium ${
                                appOpsTab === t.k
                                  ? 'bg-indigo-600 text-white'
                                  : 'bg-slate-900 text-slate-400'
                              }`}
                            >
                              {t.label}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="max-h-52 overflow-y-auto bg-slate-950 border border-slate-800 rounded p-2.5 text-xs font-mono space-y-1">
                        {(appops[appOpsTab] || []).map((item: any, idx: number) => (
                          <div key={idx} className="text-slate-300">
                            {typeof item === 'string' ? item : `${item.package} (${item.op || ''})`}
                          </div>
                        ))}
                      </div>
                    </Card>
                  </div>

                  {/* Searchable System Settings Explorer */}
                  <Card className="p-5 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-200">
                          🔎 Full System Settings Explorer (`global` / `secure` / `system`)
                        </h3>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Inspect all key-value entries captured across Android configuration namespaces.
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <select
                          value={settingsNamespace}
                          onChange={(e) => setSettingsNamespace(e.target.value as any)}
                          className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                        >
                          <option value="all">All Namespaces</option>
                          <option value="global">global</option>
                          <option value="secure">secure</option>
                          <option value="system">system</option>
                        </select>
                        <div className="relative">
                          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
                          <input
                            type="text"
                            value={settingsSearch}
                            onChange={(e) => setSettingsSearch(e.target.value)}
                            placeholder="Search key or value..."
                            className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 w-64"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-3 text-xs text-slate-300 space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-indigo-300 text-[11px]">
                        <Info className="w-3.5 h-3.5" />
                        <span>System Settings Reference:</span>
                      </div>
                      <p className="text-slate-400 leading-relaxed text-[11px]">
                        Dumps from `settings list` define OS telemetry, power management states, radio policies, and peripheral polling intervals.
                        AI diagnostics cross-reference these keys (e.g. `wifi_scan_always_enabled`, `deviceidle_constants`, `location_mode`) to flag rogue power drainers.
                      </p>
                    </div>

                    <div className="max-h-80 overflow-y-auto border border-slate-800 rounded-lg">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead className="bg-slate-900 sticky top-0">
                          <tr className="border-b border-slate-800 text-slate-400">
                            <th className="py-2 px-3 w-28">Namespace</th>
                            <th className="py-2 px-3">Key</th>
                            <th className="py-2 px-3">Value</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {filteredSettingsRows.map((r, i) => (
                            <tr key={`${r.namespace}-${r.key}-${i}`} className="hover:bg-slate-900/50">
                              <td className="py-1.5 px-3 text-indigo-400">{r.namespace}</td>
                              <td className="py-1.5 px-3 text-slate-200">{r.key}</td>
                              <td className="py-1.5 px-3 text-slate-300 break-all">{r.value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                </div>
              )}

              {/* SUB-TAB 2: WIFI ROUTER ENVIRONMENT */}
              {activeSubTab === 'wifi' && (
                <div className="space-y-6">
                  <Card className="p-5 space-y-4">
                    <h3 className="text-sm font-semibold text-slate-200">
                      ➕ Add New WiFi Router / AP (AI Specification Auto-Discovery)
                    </h3>
                    <div className="flex flex-wrap items-center gap-3">
                      <Input
                        value={newRouterBrand}
                        onChange={(e) => setNewRouterBrand(e.target.value)}
                        placeholder="Brand (e.g. Ubiquiti, ASUS, Fritz!Box)"
                        className="text-xs w-56"
                      />
                      <Input
                        value={newRouterModel}
                        onChange={(e) => setNewRouterModel(e.target.value)}
                        placeholder="Model (e.g. UniFi U6-Pro, RT-AX86U)"
                        className="text-xs flex-1 min-w-[200px]"
                      />
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleDiscoverRouter(true)}
                        disabled={discoveringRouter || (!newRouterBrand.trim() && !newRouterModel.trim())}
                        className="text-xs"
                      >
                        {discoveringRouter ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Sparkles className="w-3.5 h-3.5" />
                        )}
                        <span>🔍 Auto-Discover Specs & Save Router</span>
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDiscoverRouter(false)}
                        disabled={discoveringRouter || (!newRouterBrand.trim() && !newRouterModel.trim())}
                        className="text-xs"
                      >
                        <span>➕ Create Empty</span>
                      </Button>
                    </div>
                  </Card>

                  {routers.length > 0 && (
                    <Card className="p-5 space-y-4">
                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
                        <div className="flex items-center gap-3">
                          <select
                            value={selectedRouterId || ''}
                            onChange={(e) => {
                              const id = Number(e.target.value);
                              setSelectedRouterId(id);
                              const found = routers.find((r) => r.id === id);
                              if (found) setEditingRouter(found);
                            }}
                            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200"
                          >
                            {routers.map((r) => (
                              <option key={r.id} value={r.id}>
                                {r.is_active ? '🟢 ' : '⚪ '}
                                {r.router_name} ({r.brand} {r.model})
                              </option>
                            ))}
                          </select>

                          <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={editingRouter.is_active === 1}
                              onChange={(e) =>
                                setEditingRouter({
                                  ...editingRouter,
                                  is_active: e.target.checked ? 1 : 0
                                })
                              }
                            />
                            <span>Include in AI Audit & Consultation Context</span>
                          </label>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={handleSaveRouterChanges}
                            disabled={savingRouter}
                            className="text-xs"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Save Router Profile</span>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleDeleteRouter}
                            className="text-xs text-rose-400"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <label className="text-[11px] text-slate-400 block mb-1">Router Display Name</label>
                          <Input
                            value={editingRouter.router_name || ''}
                            onChange={(e) => setEditingRouter({ ...editingRouter, router_name: e.target.value })}
                            className="text-xs"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-400 block mb-1">Brand</label>
                          <Input
                            value={editingRouter.brand || ''}
                            onChange={(e) => setEditingRouter({ ...editingRouter, brand: e.target.value })}
                            className="text-xs"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-400 block mb-1">Model</label>
                          <Input
                            value={editingRouter.model || ''}
                            onChange={(e) => setEditingRouter({ ...editingRouter, model: e.target.value })}
                            className="text-xs"
                          />
                        </div>
                        {[
                          { key: 'wifi_standard', label: 'WiFi Generation (WiFi 6/6E/7)' },
                          { key: 'bands', label: 'Supported Bands (2.4/5/6 GHz)' },
                          { key: 'dtim_default', label: 'DTIM Period (e.g. 1 vs 3)' },
                          { key: 'beacon_interval', label: 'Beacon Interval (e.g. 100ms)' },
                          { key: 'twt_support', label: 'Target Wake Time (802.11ax TWT)' },
                          { key: 'uapsd_support', label: 'U-APSD / WMM Power Save' }
                        ].map((field) => (
                          <div key={field.key}>
                            <label className="text-[11px] text-slate-400 block mb-1">
                              {field.label}
                            </label>
                            <Input
                              value={editingSpecs[field.key] || ''}
                              onChange={(e) =>
                                setEditingRouter({
                                  ...editingRouter,
                                  specs_json: {
                                    ...editingSpecs,
                                    [field.key]: e.target.value
                                  }
                                })
                              }
                              className="text-xs"
                            />
                          </div>
                        ))}
                      </div>

                      <div>
                        <label className="text-xs text-slate-400 block mb-1">
                          Custom Configuration Notes & Standby Observations
                        </label>
                        <textarea
                          rows={3}
                          value={editingRouter.notes || ''}
                          onChange={(e) =>
                            setEditingRouter({ ...editingRouter, notes: e.target.value })
                          }
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200"
                        />
                      </div>
                    </Card>
                  )}
                </div>
              )}

              {/* SUB-TAB 3: PROFILE CONSULTATION CHAT */}
              {activeSubTab === 'chat' && activeProfile && (
                <div className="h-[620px] bg-slate-900/40 border border-slate-800 rounded-xl p-4">
                  <ChatWorkspace reportId={-activeProfile.id} />
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};
