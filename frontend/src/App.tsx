import React, { useState, useEffect } from 'react';
import { api } from './api/client';
import { ReportSummary, ReportDetail, Settings } from './types/api';
import { Header, ChatLayoutMode, WorkspaceViewMode } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { UploadModal } from './components/reports/UploadModal';
import { ComparativeView } from './components/reports/ComparativeView';
import { SettingsModal } from './components/settings/SettingsModal';
import { ReportWorkspace } from './components/workspace/ReportWorkspace';
import { ChatWorkspace } from './components/chat/ChatWorkspace';
import { FloatingWindow } from './components/chat/FloatingWindow';
import { DeviceProfileView } from './components/profiles/DeviceProfileView';
import { MasterSynthesisView } from './components/synthesis/MasterSynthesisView';
import { AccountingView } from './components/accounting/AccountingView';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import { Zap, Loader2 } from 'lucide-react';

export default function App() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [currentReport, setCurrentReport] = useState<ReportDetail | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [selectedReportIds, setSelectedReportIds] = useState<number[]>([]);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceViewMode>('single');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [chatLayout, setChatLayout] = useState<ChatLayoutMode>('split');

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
    setWorkspaceView('single');
  };

  const showSidebar = workspaceView === 'single' || workspaceView === 'compare';

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Header */}
      <Header
        settings={settings}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        workspaceView={workspaceView}
        onSelectWorkspaceView={setWorkspaceView}
        selectedCount={selectedReportIds.length}
        chatLayout={chatLayout}
        onSelectChatLayout={setChatLayout}
      />

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Sidebar (shown in Single Report and Merged & Compare views) */}
        {showSidebar && (
          <Sidebar
            reports={reports}
            selectedReportId={selectedReportId}
            onSelectReport={(id) => {
              setSelectedReportId(id);
              setWorkspaceView('single');
            }}
            onDeleteReport={handleDeleteReport}
            isComparativeMode={workspaceView === 'compare'}
            selectedReportIds={selectedReportIds}
            onToggleReportSelection={handleToggleReportSelection}
          />
        )}

        {/* Workspace Area */}
        <main className="flex-1 flex flex-col overflow-hidden bg-slate-950">
          {loading ? (
            <div className="flex-1 flex items-center justify-center text-slate-500 gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading Battery Oracle Workspace...</span>
            </div>
          ) : workspaceView === 'profile' ? (
            <div className="flex-1 overflow-y-auto p-6">
              <DeviceProfileView />
            </div>
          ) : workspaceView === 'master' ? (
            <div className="flex-1 overflow-y-auto p-6">
              <MasterSynthesisView />
            </div>
          ) : workspaceView === 'accounting' ? (
            <div className="flex-1 overflow-y-auto p-6">
              <AccountingView />
            </div>
          ) : workspaceView === 'compare' ? (
            <div className="flex-1 overflow-y-auto p-6">
              <ComparativeView
                selectedReportIds={selectedReportIds}
                reports={reports}
              />
            </div>
          ) : loadingReport ? (
            <div className="flex-1 flex items-center justify-center text-slate-500 gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading report telemetry...</span>
            </div>
          ) : currentReport ? (
            chatLayout === 'split' ? (
              // Side-by-side Resizable Panels
              <PanelGroup direction="horizontal" className="flex-1 w-full h-full">
                <Panel defaultSize={55} minSize={30} className="overflow-y-auto p-6">
                  <ReportWorkspace
                    report={currentReport}
                    nightStartHour={settings?.night_start_hour}
                    nightEndHour={settings?.night_end_hour}
                    onRefreshReport={() => {
                      if (selectedReportId) loadReportDetail(selectedReportId);
                    }}
                  />
                </Panel>
                <PanelResizeHandle className="w-1.5 bg-slate-800 hover:bg-indigo-500 transition-colors cursor-col-resize" />
                <Panel defaultSize={45} minSize={25} className="p-4 flex flex-col h-full bg-slate-900/30">
                  <ChatWorkspace reportId={currentReport.id} />
                </Panel>
              </PanelGroup>
            ) : chatLayout === 'stacked' ? (
              // Stacked Top / Bottom Resizable Panels
              <PanelGroup direction="vertical" className="flex-1 w-full h-full">
                <Panel defaultSize={60} minSize={30} className="overflow-y-auto p-6">
                  <ReportWorkspace
                    report={currentReport}
                    nightStartHour={settings?.night_start_hour}
                    nightEndHour={settings?.night_end_hour}
                    onRefreshReport={() => {
                      if (selectedReportId) loadReportDetail(selectedReportId);
                    }}
                  />
                </Panel>
                <PanelResizeHandle className="h-1.5 bg-slate-800 hover:bg-indigo-500 transition-colors cursor-row-resize" />
                <Panel defaultSize={40} minSize={20} className="p-4 flex flex-col h-full bg-slate-900/30">
                  <ChatWorkspace reportId={currentReport.id} />
                </Panel>
              </PanelGroup>
            ) : (
              // Floating / Full View
              <div className="flex-1 overflow-y-auto p-6">
                <ReportWorkspace
                  report={currentReport}
                  nightStartHour={settings?.night_start_hour}
                  nightEndHour={settings?.night_end_hour}
                  onRefreshReport={() => {
                    if (selectedReportId) loadReportDetail(selectedReportId);
                  }}
                />
                <FloatingWindow
                  isOpen={chatLayout === 'floating'}
                  onClose={() => setChatLayout('hidden')}
                  onDock={() => setChatLayout('split')}
                  title={`AI Investigation - ${currentReport.custom_name || currentReport.filename}`}
                >
                  <ChatWorkspace reportId={currentReport.id} />
                </FloatingWindow>
              </div>
            )
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
        defaultTimezone={settings?.device_timezone || 'Europe/Warsaw'}
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
