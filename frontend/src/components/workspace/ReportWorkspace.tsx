import React, { useEffect, useState, useCallback } from 'react';
import { ScopeSelector, AnalysisScope } from './ScopeSelector';
import { KpiGrid } from './KpiGrid';
import { DischargeChart } from './DischargeChart';
import { TopConsumersChart } from './TopConsumersChart';
import { DiagnosisCard } from './DiagnosisCard';
import { ReportDetail, TelemetryResponse } from '../../types/api';
import { api } from '../../api/client';
import { Badge } from '../ui/Badge';
import { useDialog } from '../ui/DialogContext';
import { Smartphone, Calendar, FileText, Cpu, Edit3, AlignLeft } from 'lucide-react';
import { EditReportModal } from './EditReportModal';

interface ReportWorkspaceProps {
  report: ReportDetail;
  onRefreshReport: () => void;
  nightStartHour?: number;
  nightEndHour?: number;
  activeScope?: AnalysisScope;
  onScopeChange?: (scope: AnalysisScope) => void;
}

export const ReportWorkspace: React.FC<ReportWorkspaceProps> = ({
  report,
  onRefreshReport,
  nightStartHour = 23,
  nightEndHour = 7,
  activeScope,
  onScopeChange
}) => {
  const { showError } = useDialog();
  const [internalScope, setInternalScope] = useState<AnalysisScope>('all');
  const scope = activeScope ?? internalScope;
  const setScope = onScopeChange ?? setInternalScope;

  const [customStart, setCustomStart] = useState<string | undefined>(undefined);
  const [customEnd, setCustomEnd] = useState<string | undefined>(undefined);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [isLoadingTelemetry, setIsLoadingTelemetry] = useState(false);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Reset custom window state when switching reports
  useEffect(() => {
    setCustomStart(undefined);
    setCustomEnd(undefined);
  }, [report.id]);

  // Load telemetry when report or scope changes
  const fetchTelemetry = useCallback(async (selectedScope: AnalysisScope, startIso?: string, endIso?: string) => {
    setIsLoadingTelemetry(true);
    try {
      const data = await api.getTelemetry(report.id, selectedScope, startIso, endIso);
      setTelemetry(data);
    } catch (err) {
      console.error('Failed to load telemetry slice:', err);
      showError(err, 'Loading Telemetry Slice');
    } finally {
      setIsLoadingTelemetry(false);
    }
  }, [report.id, showError]);

  useEffect(() => {
    if (scope === 'custom') {
      fetchTelemetry('custom', customStart, customEnd);
    } else {
      fetchTelemetry(scope);
    }
  }, [fetchTelemetry, scope, customStart, customEnd, nightStartHour, nightEndHour]);

  const handleScopeChange = (newScope: AnalysisScope) => {
    if (newScope === 'custom' && !customStart && !customEnd) {
      setCustomStart(telemetry?.session_bounds?.min_time || undefined);
      setCustomEnd(telemetry?.session_bounds?.max_time || undefined);
    }
    setScope(newScope);
  };

  const handleApplyCustomWindow = (startIso: string, endIso: string) => {
    setCustomStart(startIso);
    setCustomEnd(endIso);
    fetchTelemetry('custom', startIso, endIso);
  };

  const handleSaveNightWindow = async (startIso: string, endIso: string) => {
    try {
      await api.updateReport(report.id, {
        custom_night_start: startIso,
        custom_night_end: endIso
      });
      onRefreshReport();
      await fetchTelemetry(scope, customStart, customEnd);
    } catch (err) {
      showError(err, 'Saving Custom Night Window');
    }
  };

  const handleResetNightWindow = async () => {
    try {
      await api.updateReport(report.id, {
        reset_night_window: true
      });
      onRefreshReport();
      await fetchTelemetry(scope, customStart, customEnd);
    } catch (err) {
      showError(err, 'Resetting Night Window to Auto-Detected Bounds');
    }
  };

  const handleDiagnose = async () => {
    setIsDiagnosing(true);
    try {
      await api.diagnoseReport(
        report.id,
        scope,
        scope === 'custom' ? customStart : undefined,
        scope === 'custom' ? customEnd : undefined
      );
      onRefreshReport();
      await fetchTelemetry(scope, customStart, customEnd);
    } catch (err) {
      console.error('Diagnosis failed:', err);
      showError(err, 'Re-Running AI Diagnosis');
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleExportMarkdown = () => {
    const url = api.getExportReportUrl(report.id, scope);
    window.open(url, '_blank');
  };

  // Convert timeline to DischargePoint[]
  const dischargeData = (telemetry?.timeline || []).map((t) => ({
    timestamp: t.timestamp,
    battery_level: t.battery_level,
    is_screen_on: t.screen_state === 'on' ? true : (t.screen_state === 'off' ? false : undefined)
  }));

  const topDrainer = telemetry?.components && telemetry.components.length > 0 ? telemetry.components[0] : null;

  return (
    <div className="space-y-6 pb-12">
      {/* Device Info & Metadata Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
              <Smartphone className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-100">
                  {report.custom_name || report.filename}
                </h1>
                <Badge variant="scope">
                  {report.device_info || 'Android Device'}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-4 mt-1 text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  {report.filename}
                </span>
                {report.timestamp_str && (
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    {report.timestamp_str}
                  </span>
                )}
                {report.created_at && (
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-slate-500" />
                    Imported: {new Date(report.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsEditModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors shadow-sm"
              title="Edit report name and description notes"
            >
              <Edit3 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Edit Details</span>
            </button>
          </div>
        </div>

        {/* Notes / Description Section */}
        {report.description ? (
          <div className="mt-4 pt-3.5 border-t border-slate-800/80 flex items-start gap-2.5 text-xs text-slate-300 bg-slate-950/50 px-3.5 py-2.5 rounded-lg border border-slate-800/60">
            <AlignLeft className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <span className="font-semibold text-slate-400 mr-2 uppercase text-[10px] tracking-wider">Experiment Notes:</span>
              <span className="text-slate-200 leading-relaxed italic">{report.description}</span>
            </div>
            <button
              type="button"
              onClick={() => setIsEditModalOpen(true)}
              className="text-slate-500 hover:text-indigo-400 p-0.5 transition-colors shrink-0"
              title="Edit notes"
            >
              <Edit3 className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="mt-3.5 pt-2.5 border-t border-slate-800/40 flex items-center justify-between text-xs text-slate-500">
            <span className="italic">No description notes added for this report.</span>
            <button
              type="button"
              onClick={() => setIsEditModalOpen(true)}
              className="text-indigo-400 hover:text-indigo-300 hover:underline text-[11px] font-medium"
            >
              + Add Notes
            </button>
          </div>
        )}
      </div>

      {/* Scope Selector */}
      <ScopeSelector
        currentScope={scope}
        onSelectScope={handleScopeChange}
        isLoading={isLoadingTelemetry}
        nightBounds={telemetry?.night_bounds}
        sessionBounds={telemetry?.session_bounds}
        customStart={customStart}
        customEnd={customEnd}
        onApplyCustomWindow={handleApplyCustomWindow}
        onSaveNightWindow={handleSaveNightWindow}
        onResetNightWindow={handleResetNightWindow}
      />

      {/* KPI Cards Grid */}
      {telemetry?.kpis ? (
        <KpiGrid kpis={telemetry.kpis} topConsumer={topDrainer} />
      ) : (
        <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-lg text-center text-sm text-slate-500">
          Loading KPI telemetry metrics...
        </div>
      )}

      {/* Charts Grid: Discharge curve + Top energy drainers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DischargeChart
          data={dischargeData}
          nightStartHour={nightStartHour}
          nightEndHour={nightEndHour}
          customNightStart={telemetry?.night_bounds?.is_custom ? (telemetry?.night_bounds?.start || report.custom_night_start) : null}
          customNightEnd={telemetry?.night_bounds?.is_custom ? (telemetry?.night_bounds?.end || report.custom_night_end) : null}
          activeScope={scope}
          hideNightShadingToggle={scope === 'night'}
        />
        <TopConsumersChart consumers={telemetry?.components || []} />
      </div>

      {/* AI Diagnostic Summary Card */}
      <DiagnosisCard
        diagnosisMarkdown={
          report.analyses?.[scope]?.text ||
          (scope === 'all' ? report.initial_analysis : undefined)
        }
        isDiagnosing={isDiagnosing}
        onDiagnose={handleDiagnose}
        onExportMarkdown={handleExportMarkdown}
        scope={scope}
      />

      {/* Edit Report Name & Description Modal */}
      <EditReportModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        report={report}
        onSaved={onRefreshReport}
      />
    </div>
  );
};
