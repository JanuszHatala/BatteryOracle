import React, { useState, useEffect } from 'react';
import { api } from './api/client';
import { ReportSummary, ReportDetail, Settings } from './types/api';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { UploadModal } from './components/reports/UploadModal';
import { ComparativeView } from './components/reports/ComparativeView';
import { SettingsModal } from './components/settings/SettingsModal';
import { ReportWorkspace } from './components/workspace/ReportWorkspace';
import { Zap, Loader2 } from 'lucide-react';

export default function App() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [currentReport, setCurrentReport] = useState<ReportDetail | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [selectedReportIds, setSelectedReportIds] = useState<number[]>([]);
  const [isComparativeMode, setIsComparativeMode] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [reps, s] = await Promise.all([
        api.getReports(),
        api.getSettings().catch(() => null)
      ]);
      setReports(reps);
      if (s) setSettings(s);
      if (reps.length > 0 && selectedReportId === null) {
        setSelectedReportId(reps[0].id);
      }
    } catch (err) {
      console.error('Failed to load initial data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadReportDetail = async (id: number) => {
    setLoadingReport(true);
    try {
      const rep = await api.getReport(id);
      setCurrentReport(rep);
    } catch (err) {
      console.error('Failed to load report detail', err);
    } finally {
      setLoadingReport(false);
    }
  };

  useEffect(() => {
    if (selectedReportId) {
      loadReportDetail(selectedReportId);
    } else {
      setCurrentReport(null);
    }
  }, [selectedReportId]);

  const handleToggleReportSelection = (id: number) => {
    setSelectedReportIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleDeleteReport = async (id: number) => {
    try {
      await api.deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      setSelectedReportIds((prev) => prev.filter((x) => x !== id));
      if (selectedReportId === id) {
        const remaining = reports.filter((r) => r.id !== id);
        setSelectedReportId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (err: any) {
      alert(`Failed to delete report: ${err.message}`);
    }
  };

  const handleUploadSuccess = (report: ReportDetail) => {
    loadData();
    setSelectedReportId(report.id);
    setCurrentReport(report);
    setIsComparativeMode(false);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Header */}
      <Header
        settings={settings}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isComparativeMode={isComparativeMode}
        onToggleComparativeMode={() => setIsComparativeMode(!isComparativeMode)}
        selectedCount={selectedReportIds.length}
      />

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Sidebar */}
        <Sidebar
          reports={reports}
          selectedReportId={selectedReportId}
          onSelectReport={(id) => {
            setSelectedReportId(id);
            setIsComparativeMode(false);
          }}
          onDeleteReport={handleDeleteReport}
          isComparativeMode={isComparativeMode}
          selectedReportIds={selectedReportIds}
          onToggleReportSelection={handleToggleReportSelection}
        />

        {/* Workspace Area */}
        <main className="flex-1 flex flex-col overflow-y-auto bg-slate-950 p-6">
          {loading ? (
            <div className="flex-1 flex items-center justify-center text-slate-500 gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading Battery Oracle Workspace...</span>
            </div>
          ) : isComparativeMode ? (
            <ComparativeView
              selectedReportIds={selectedReportIds}
              reports={reports}
            />
          ) : loadingReport ? (
            <div className="flex-1 flex items-center justify-center text-slate-500 gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading report telemetry...</span>
            </div>
          ) : currentReport ? (
            <ReportWorkspace
              report={currentReport}
              onRefreshReport={() => {
                if (selectedReportId) loadReportDetail(selectedReportId);
              }}
            />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-slate-200">No Report Selected</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Select an Android bugreport from the sidebar or click "Upload Bugreport" above to begin.
              </p>
            </div>
          )}
        </main>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        defaultTimezone={settings?.device_timezone || 'UTC'}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentSettings={settings}
        onSettingsUpdated={(newS) => setSettings(newS)}
      />
    </div>
  );
}
