import React, { useState, useEffect } from 'react';
import { api } from './api/client';
import { ReportSummary } from './types/api';
import { Button } from './components/ui/Button';
import { Badge } from './components/ui/Badge';
import { Zap, Activity } from 'lucide-react';

export default function App() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReports()
      .then(setReports)
      .catch((err) => console.error('Failed to load reports', err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4 shadow-lg shadow-emerald-950/40">
          <Zap className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white mb-2">BatteryOracle 2.0 Workspace</h1>
        <p className="text-sm text-slate-400 max-w-md mb-6">
          High-performance Android bugreport telemetry diagnostics, discharge analytics, and AI reasoning.
        </p>
        <div className="flex items-center gap-3">
          <Badge variant="optimal">FastAPI Connected</Badge>
          <Badge variant="scope">React 19 SPA</Badge>
          <Badge variant="neutral">{loading ? 'Loading...' : `${reports.length} Reports`}</Badge>
        </div>
      </div>
    </div>
  );
}
