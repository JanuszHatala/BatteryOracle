import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { MasterSynthesisResponse } from '../../types/api';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { ChatWorkspace } from '../chat/ChatWorkspace';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Brain,
  Sparkles,
  Download,
  MessageSquare,
  FileText,
  Loader2,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

export const MasterSynthesisView: React.FC = () => {
  const [data, setData] = useState<MasterSynthesisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<'blueprint' | 'chat'>('blueprint');
  const [showScorecard, setShowScorecard] = useState(true);

  const loadSynthesis = async () => {
    setLoading(true);
    try {
      const res = await api.getMasterSynthesis();
      setData(res);
    } catch (err) {
      console.error('Failed to load master synthesis:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSynthesis();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.generateMasterSynthesis();
      setData(res);
    } catch (err: any) {
      alert(`Master Synthesis generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleExportMarkdown = () => {
    if (!data?.synthesis_text) return;
    const blob = new Blob([data.synthesis_text], {
      type: 'text/markdown;charset=utf-8'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'battery_oracle_master_synthesis.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Loading Multi-Day Experiment Scorecard & Synthesis...</span>
      </div>
    );
  }

  const scorecard = data?.scorecard || [];

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            <span>🧠 Master Synthesis & Optimization Blueprint</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Holistic cross-report retrospective across all {scorecard.length} imported bugreports ({data?.date_range || 'All Sessions'}).
          </p>
        </div>

        <div className="flex items-center gap-2">
          {data?.updated_at && (
            <Badge variant="scope">Last Synthesized: {data.updated_at}</Badge>
          )}
          {data?.synthesis_text && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExportMarkdown}
              className="text-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>📥 Export Blueprint (.md)</span>
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={handleGenerate}
            disabled={generating || scorecard.length === 0}
            className="text-xs"
          >
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>
              {generating
                ? 'Synthesizing All Reports...'
                : '✨ Generate / Refresh Master Synthesis'}
            </span>
          </Button>
        </div>
      </div>

      {/* Multi-Day Experiment Scorecard Table */}
      <Card className="overflow-hidden">
        <button
          type="button"
          onClick={() => setShowScorecard(!showScorecard)}
          className="w-full flex items-center justify-between px-5 py-3.5 text-left bg-slate-900/70 hover:bg-slate-900 transition-colors"
        >
          <span className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            {showScorecard ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
            <span>📊 Multi-Day Experiment Scorecard ({scorecard.length} Reports)</span>
          </span>
          <span className="text-xs text-slate-400">
            Click to {showScorecard ? 'collapse' : 'expand'} chronological telemetry table
          </span>
        </button>

        {showScorecard && (
          <div className="overflow-x-auto max-h-80 border-t border-slate-800">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-950 sticky top-0 z-10">
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">Session Name</th>
                  <th className="py-2.5 px-3">Recorded Interval</th>
                  <th className="py-2.5 px-3">Full Drop Rate</th>
                  <th className="py-2.5 px-3">Night Standby Rate</th>
                  <th className="py-2.5 px-3">Total Loss</th>
                  <th className="py-2.5 px-3">Night Drop</th>
                  <th className="py-2.5 px-3">Notes / Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {scorecard.map((row) => (
                  <tr key={row.report_id} className="hover:bg-slate-900/50">
                    <td className="py-2 px-3 text-indigo-400">#{row.report_id}</td>
                    <td className="py-2 px-3 font-sans font-medium text-slate-200">
                      {row.session_name}
                    </td>
                    <td className="py-2 px-3 text-slate-400">{row.recorded_interval}</td>
                    <td className="py-2 px-3 text-slate-300">{row.full_drop_rate}</td>
                    <td className="py-2 px-3 text-amber-300 font-semibold">
                      {row.night_standby_rate}
                    </td>
                    <td className="py-2 px-3 text-slate-300">{row.total_loss}</td>
                    <td className="py-2 px-3 text-emerald-400">{row.night_drop}</td>
                    <td className="py-2 px-3 text-slate-400 truncate max-w-[240px]" title={row.notes}>
                      {row.notes || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Sub-Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('blueprint')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'blueprint'
              ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>📜 Master Retrospective & Action Plan</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('chat')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'chat'
              ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>💬 Master Experiment Consultation Chat</span>
        </button>
      </div>

      {/* Sub-Tab 1: Master Blueprint Markdown */}
      {activeTab === 'blueprint' && (
        <Card className="p-6">
          {data?.synthesis_text ? (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {data.synthesis_text}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="py-12 text-center space-y-3">
              <Brain className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-200">
                No Master Synthesis Generated Yet
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Click "✨ Generate / Refresh Master Synthesis" above to analyze all {scorecard.length} reports and build a prioritized optimization action plan.
              </p>
            </div>
          )}
        </Card>
      )}

      {/* Sub-Tab 2: Master Experiment Consultation Chat */}
      {activeTab === 'chat' && (
        <div className="h-[620px] bg-slate-900/40 border border-slate-800 rounded-xl p-4">
          <ChatWorkspace reportId={-999999} />
        </div>
      )}
    </div>
  );
};
