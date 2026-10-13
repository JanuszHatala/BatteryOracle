import React, { useEffect, useState, useCallback } from 'react';
import { ScopeSelector, AnalysisScope } from './ScopeSelector';
import { KpiGrid } from './KpiGrid';
import { DischargeChart } from './DischargeChart';
import { TopConsumersChart } from './TopConsumersChart';
import { DiagnosisCard } from './DiagnosisCard';
import { ReportDetail, TelemetryResponse } from '../../types/api';
import { api } from '../../api/client';
import { Badge } from '../ui/Badge';
import { Smartphone, Calendar, FileText, Cpu } from 'lucide-react';

interface ReportWorkspaceProps {
  report: ReportDetail;
  onRefreshReport: () => void;
  nightStartHour?: number;
  nightEndHour?: number;
}

export const ReportWorkspace: React.FC<ReportWorkspaceProps> = ({
  report,
  onRefreshReport,
  nightStartHour = 23,
  nightEndHour = 7
}) => {
  const [scope, setScope] = useState<AnalysisScope>('night');
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [isLoadingTelemetry, setIsLoadingTelemetry] = useState(false);
  const [isDiagnosing, setIsDiagnosing] = useState(false);

  // Load telemetry when report or scope changes
  const fetchTelemetry = useCallback(async (selectedScope: AnalysisScope) => {
    setIsLoadingTelemetry(true);
    try {
      const data = await api.getTelemetry(report.id, selectedScope);
      setTelemetry(data);
    } catch (err) {
      console.error('Failed to load telemetry slice:', err);
    } finally {
      setIsLoadingTelemetry(false);
    }
  }, [report.id]);

  useEffect(() => {
    fetchTelemetry(scope);
  }, [fetchTelemetry, scope]);

  const handleScopeChange = (newScope: AnalysisScope) => {
    setScope(newScope);
  };

  const handleDiagnose = async () => {
    setIsDiagnosing(true);
    try {
      await api.diagnoseReport(report.id, scope);
      onRefreshReport();
      await fetchTelemetry(scope);
    } catch (err) {
      console.error('Diagnosis failed:', err);
      alert('Diagnosis generation failed. Check your API settings / LLM key.');
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
    is_screen_on: t.screen_state === 'on'
  }));

  const topDrainer = telemetry?.components && telemetry.components.length > 0 ? telemetry.components[0] : null;

  return (
    <div className="space-y-6 pb-12">
      {/* Device Info & Metadata Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
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
        </div>
      </div>

      {/* Scope Selector */}
      <ScopeSelector
        currentScope={scope}
        onSelectScope={handleScopeChange}
        isLoading={isLoadingTelemetry}
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
        />
        <TopConsumersChart consumers={telemetry?.components || []} />
      </div>

      {/* AI Diagnostic Summary Card */}
      <DiagnosisCard
        diagnosisMarkdown={report.initial_analysis || undefined}
        isDiagnosing={isDiagnosing}
        onDiagnose={handleDiagnose}
        onExportMarkdown={handleExportMarkdown}
      />
    </div>
  );
};
