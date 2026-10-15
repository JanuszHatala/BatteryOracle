import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { AccountingDashboardResponse } from '../../types/api';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import {
  Coins,
  Folder,
  MessageSquare,
  Calendar,
  RefreshCw,
  Loader2
} from 'lucide-react';

export const AccountingView: React.FC = () => {
  const [data, setData] = useState<AccountingDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'by_report' | 'by_thread' | 'by_date'>('by_report');

  const loadAccounting = async () => {
    setLoading(true);
    try {
      const res = await api.getAccounting();
      setData(res);
    } catch (err) {
      console.error('Failed to load accounting stats:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccounting();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 gap-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Loading Token & Cost Accounting...</span>
      </div>
    );
  }

  const totals = data?.totals || {
    request_count: 0,
    total_prompt: 0,
    total_completion: 0,
    total_cached: 0,
    total_tokens: 0,
    total_cost: 0
  };

  const cacheHitPct =
    totals.total_prompt > 0
      ? ((totals.total_cached / totals.total_prompt) * 100).toFixed(1)
      : '0.0';

  const byReport = data?.by_report || [];
  const byThread = data?.by_thread || [];
  const overTime = data?.over_time || [];

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Coins className="w-5 h-5 text-amber-400" />
            <span>💰 Token & Cost Accounting</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Track LLM token consumption, prompt context caching savings, and estimated API spend across all bugreports and threads.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={loadAccounting}
          className="text-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Stats</span>
        </Button>
      </div>

      {/* 6 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <Card className="p-4">
          <div className="text-xs text-slate-400">Total Tokens</div>
          <div className="text-xl font-bold text-slate-100 mt-1 font-mono">
            {(totals.total_tokens || 0).toLocaleString()}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-slate-400">Prompt Tokens</div>
          <div className="text-xl font-bold text-indigo-400 mt-1 font-mono">
            {(totals.total_prompt || 0).toLocaleString()}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-slate-400">Completion Tokens</div>
          <div className="text-xl font-bold text-sky-400 mt-1 font-mono">
            {(totals.total_completion || 0).toLocaleString()}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-slate-400">Cached Tokens</div>
          <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">
            {(totals.total_cached || 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-emerald-500 mt-0.5">
            {cacheHitPct}% prompt cache hit
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-slate-400">Total Cost (USD)</div>
          <div className="text-xl font-bold text-amber-400 mt-1 font-mono">
            ${Number(totals.total_cost || 0).toFixed(4)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-slate-400">LLM Requests</div>
          <div className="text-xl font-bold text-slate-200 mt-1 font-mono">
            {(totals.request_count || 0).toLocaleString()}
          </div>
        </Card>
      </div>

      {/* 3 Sub-Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('by_report')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'by_report'
              ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Folder className="w-3.5 h-3.5" />
          <span>📁 Breakdown by Bugreport ({byReport.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('by_thread')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'by_thread'
              ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>🧵 Breakdown by Thread ({byThread.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('by_date')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'by_date'
              ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>📅 Activity Over Time ({overTime.length})</span>
        </button>
      </div>

      {/* TAB 1: Breakdown by Bugreport */}
      {activeTab === 'by_report' && (
        <div className="space-y-6">
          {byReport.length > 0 && (
            <Card className="p-4 h-72 flex flex-col">
              <h3 className="text-sm font-semibold text-slate-200 mb-2">
                Estimated Cost (USD) per Report / Context
              </h3>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={byReport.slice(0, 15)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                    <XAxis
                      dataKey="report_name"
                      stroke="#64748b"
                      fontSize={11}
                      tickFormatter={(v: string) => (v && v.length > 16 ? `${v.slice(0, 14)}…` : v)}
                    />
                    <YAxis stroke="#64748b" fontSize={11} unit="$" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.5rem',
                        fontSize: '12px'
                      }}
                      itemStyle={{ color: '#f1f5f9' }}
                      labelStyle={{ color: '#94a3b8' }}
                      formatter={(val: any) => [`$${Number(val).toFixed(4)}`, 'Cost USD']}
                    />
                    <Bar dataKey="total_cost" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                  <tr>
                    <th className="py-2.5 px-3">Report / Context</th>
                    <th className="py-2.5 px-3">Prompt Tokens</th>
                    <th className="py-2.5 px-3">Completion</th>
                    <th className="py-2.5 px-3">Cached</th>
                    <th className="py-2.5 px-3">Total Tokens</th>
                    <th className="py-2.5 px-3">Est. Cost (USD)</th>
                    <th className="py-2.5 px-3">Requests</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {byReport.map((r, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/50">
                      <td className="py-2 px-3 font-sans font-medium text-slate-200">
                        {r.report_name || `Report #${r.report_id}`}
                      </td>
                      <td className="py-2 px-3 text-slate-300">
                        {(r.prompt_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-slate-300">
                        {(r.completion_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-emerald-400">
                        {(r.cached_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-indigo-300 font-semibold">
                        {(r.total_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-amber-400 font-semibold">
                        ${Number(r.total_cost || 0).toFixed(4)}
                      </td>
                      <td className="py-2 px-3 text-slate-400">{r.request_count || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: Breakdown by Thread */}
      {activeTab === 'by_thread' && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-2.5 px-3">Thread Title</th>
                  <th className="py-2.5 px-3">Report</th>
                  <th className="py-2.5 px-3">Total Tokens</th>
                  <th className="py-2.5 px-3">Est. Cost (USD)</th>
                  <th className="py-2.5 px-3">Requests</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {byThread.map((t, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/50">
                    <td className="py-2 px-3 font-sans font-medium text-slate-200">
                      {t.thread_title || `Thread #${t.thread_id}`}
                    </td>
                    <td className="py-2 px-3 font-sans text-slate-400">
                      {t.report_name}
                    </td>
                    <td className="py-2 px-3 text-indigo-300 font-semibold">
                      {(t.total_tokens || 0).toLocaleString()}
                    </td>
                    <td className="py-2 px-3 text-amber-400 font-semibold">
                      ${Number(t.total_cost || 0).toFixed(4)}
                    </td>
                    <td className="py-2 px-3 text-slate-400">{t.request_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 3: Activity Over Time */}
      {activeTab === 'by_date' && (
        <div className="space-y-6">
          {overTime.length > 0 && (
            <Card className="p-4 h-72 flex flex-col">
              <h3 className="text-sm font-semibold text-slate-200 mb-2">
                Daily Token Consumption
              </h3>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[...overTime].reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '0.5rem',
                        fontSize: '12px'
                      }}
                      itemStyle={{ color: '#f1f5f9' }}
                      labelStyle={{ color: '#94a3b8' }}
                    />
                    <Bar dataKey="total_tokens" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                  <tr>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Model</th>
                    <th className="py-2.5 px-3">Prompt Tokens</th>
                    <th className="py-2.5 px-3">Completion</th>
                    <th className="py-2.5 px-3">Cached</th>
                    <th className="py-2.5 px-3">Total Tokens</th>
                    <th className="py-2.5 px-3">Est. Cost (USD)</th>
                    <th className="py-2.5 px-3">Requests</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {overTime.map((d, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/50">
                      <td className="py-2 px-3 text-slate-200">{d.date}</td>
                      <td className="py-2 px-3 text-slate-400">{d.model}</td>
                      <td className="py-2 px-3 text-slate-300">
                        {(d.prompt_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-slate-300">
                        {(d.completion_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-emerald-400">
                        {(d.cached_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-indigo-300 font-semibold">
                        {(d.total_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-amber-400 font-semibold">
                        ${Number(d.total_cost || 0).toFixed(4)}
                      </td>
                      <td className="py-2 px-3 text-slate-400">{d.request_count || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
