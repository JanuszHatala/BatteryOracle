import React, { useState } from 'react';
import { ReportSummary, ComparativeResponse } from '../../types/api';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { api } from '../../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { GitCompare, Sparkles, Download, Loader2, AlertCircle } from 'lucide-react';

interface ComparativeViewProps {
  selectedReportIds: number[];
  reports: ReportSummary[];
}

export const ComparativeView: React.FC<ComparativeViewProps> = ({
  selectedReportIds,
  reports
}) => {
  const [scope, setScope] = useState<'night' | 'full' | 'screen_off'>('night');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComparativeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const compared = reports.filter((r) => selectedReportIds.includes(r.id));

  const handleSynthesize = async () => {
    if (selectedReportIds.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyzeComparative(selectedReportIds, scope);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate comparative synthesis.');
    } finally {
      setLoading(false);
    }
  };

  if (selectedReportIds.length < 2) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center select-none">
        <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
          <GitCompare className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-semibold text-slate-100 mb-2">Multi-Report Comparative Analysis</h3>
        <p className="text-sm text-slate-400 max-w-md mb-6">
          Select at least 2 bugreports using the checkboxes in the sidebar to compare discharge rates, identify battery regressions, and generate cross-session AI diagnoses.
        </p>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Currently selected:</span>
          <Badge variant="scope">{selectedReportIds.length} sessions</Badge>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Analysis Scope:</span>
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setScope('night')}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                scope === 'night' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🌙 Night Standby
            </button>
            <button
              onClick={() => setScope('full')}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                scope === 'full' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🌐 Full Session
            </button>
            <button
              onClick={() => setScope('screen_off')}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                scope === 'screen_off' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📴 Screen-Off
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            onClick={handleSynthesize}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-xs"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span>Synthesize Regression Analysis</span>
          </Button>

          <a
            href={api.getExportComparativeUrl(selectedReportIds, scope)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Markdown</span>
          </a>
        </div>
      </div>

      {/* Compared Reports Table */}
      <Card>
        <CardHeader>
          <h4 className="text-sm font-semibold text-slate-200">Selected Telemetry Sessions ({compared.length})</h4>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4 font-medium">Session Name</th>
                <th className="py-2.5 px-4 font-medium">Timestamp</th>
                <th className="py-2.5 px-4 font-medium">Device</th>
                <th className="py-2.5 px-4 font-medium">Rate (%/hr)</th>
                <th className="py-2.5 px-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {compared.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/30">
                  <td className="py-2.5 px-4 font-medium text-slate-100">{r.custom_name}</td>
                  <td className="py-2.5 px-4 text-slate-400">{r.timestamp_str || 'N/A'}</td>
                  <td className="py-2.5 px-4 text-slate-400">{r.device_info || 'Android'}</td>
                  <td className="py-2.5 px-4 font-mono font-medium text-emerald-400">
                    {r.rate_per_hr !== null ? `${r.rate_per_hr.toFixed(2)}%/hr` : 'N/A'}
                  </td>
                  <td className="py-2.5 px-4">
                    <Badge variant={r.status?.includes('Optimal') ? 'optimal' : 'elevated'} className="text-[10px]">
                      {r.status || 'Analyzed'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Error alert */}
      {error && (
        <div className="p-4 bg-rose-950/50 border border-rose-800/60 rounded-xl text-xs text-rose-300 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Comparative Synthesis Result */}
      {result && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <h4 className="text-sm font-semibold text-slate-100">Cross-Session AI Diagnosis & Delta Insights</h4>
            </div>
            {result.cached && (
              <Badge variant="neutral" className="text-[10px]">
                Cached Synthesis
              </Badge>
            )}
          </CardHeader>
          <CardContent className="prose prose-invert prose-sm max-w-none prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.analysis}</ReactMarkdown>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
