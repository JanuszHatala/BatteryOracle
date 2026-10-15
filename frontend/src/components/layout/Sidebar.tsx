import React, { useState } from 'react';
import { ReportSummary } from '../../types/api';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import { useDialog } from '../ui/DialogContext';
import { Search, Trash2, Smartphone, Calendar, CheckSquare, Square } from 'lucide-react';

interface SidebarProps {
  reports: ReportSummary[];
  selectedReportId: number | null;
  onSelectReport: (id: number) => void;
  onDeleteReport: (id: number) => void;
  isComparativeMode: boolean;
  selectedReportIds: number[];
  onToggleReportSelection: (id: number) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  reports,
  selectedReportId,
  onSelectReport,
  onDeleteReport,
  isComparativeMode,
  selectedReportIds,
  onToggleReportSelection
}) => {
  const { confirm } = useDialog();
  const [query, setQuery] = useState('');

  const filtered = reports.filter((r) => {
    const q = query.toLowerCase();
    return (
      r.custom_name.toLowerCase().includes(q) ||
      (r.device_info && r.device_info.toLowerCase().includes(q)) ||
      (r.timestamp_str && r.timestamp_str.toLowerCase().includes(q))
    );
  });

  const getStatusVariant = (status?: string | null) => {
    if (!status) return 'neutral';
    const s = status.toLowerCase();
    if (s.includes('optimal') || s.includes('healthy')) return 'optimal';
    if (s.includes('elevated') || s.includes('moderate')) return 'elevated';
    if (s.includes('severe') || s.includes('drain')) return 'severe';
    return 'neutral';
  };

  return (
    <aside className="w-80 border-r border-slate-800 bg-slate-900/40 flex flex-col shrink-0 select-none overflow-hidden h-full">
      {/* Search Bar & Count */}
      <div className="p-3 border-b border-slate-800/80 space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300 px-0.5">
          <span>Reports & Import ({reports.length})</span>
          {isComparativeMode && (
            <span className="text-[11px] text-indigo-400 font-medium">
              {selectedReportIds.length} selected
            </span>
          )}
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search reports or devices..."
            className="pl-9 text-xs h-9 bg-slate-950/60"
          />
        </div>
      </div>

      {/* Reports List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filtered.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500">
            {reports.length === 0 ? 'No bugreports imported yet.' : 'No reports matching search.'}
          </div>
        ) : (
          filtered.map((r) => {
            const isSelected = selectedReportId === r.id;
            const isChecked = selectedReportIds.includes(r.id);

            return (
              <div
                key={r.id}
                onClick={() => {
                  if (isComparativeMode) {
                    onToggleReportSelection(r.id);
                  } else {
                    onSelectReport(r.id);
                  }
                }}
                className={`group relative p-3 rounded-xl border text-left cursor-pointer transition-all ${
                  isSelected && !isComparativeMode
                    ? 'bg-slate-800/90 border-emerald-500/50 shadow-sm'
                    : isChecked && isComparativeMode
                    ? 'bg-indigo-950/30 border-indigo-500/60'
                    : 'bg-slate-900/30 border-slate-800/60 hover:bg-slate-800/50 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    {isComparativeMode && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleReportSelection(r.id);
                        }}
                        className="text-slate-400 hover:text-indigo-400 shrink-0"
                      >
                        {isChecked ? (
                          <CheckSquare className="w-4 h-4 text-indigo-400" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-600" />
                        )}
                      </button>
                    )}
                    <h4 className="text-xs font-semibold text-slate-100 truncate">{r.custom_name}</h4>
                  </div>

                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      const ok = await confirm({
                        title: 'Delete Bugreport',
                        message: `Are you sure you want to permanently delete report "${r.custom_name}" and all its associated chat threads?`,
                        confirmLabel: 'Delete Report',
                        variant: 'danger'
                      });
                      if (ok) {
                        onDeleteReport(r.id);
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 p-1 transition-opacity shrink-0"
                    title="Delete report"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2 text-[11px] text-slate-400 mb-2">
                  <span className="flex items-center gap-1 shrink-0">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    <span>{r.timestamp_str || 'N/A'}</span>
                  </span>
                  {r.device_info && (
                    <span className="flex items-center gap-1 truncate text-slate-500">
                      <Smartphone className="w-3 h-3 shrink-0" />
                      <span className="truncate">{r.device_info.split('|')[0].trim()}</span>
                    </span>
                  )}
                </div>

                {r.description && (
                  <p className="text-[11px] text-slate-400/90 line-clamp-1 italic mb-1.5" title={r.description}>
                    {r.description}
                  </p>
                )}

                <div className="flex items-center gap-1.5">
                  {r.rate_per_hr !== null && r.rate_per_hr !== undefined && (
                    <Badge variant={getStatusVariant(r.status)} className="text-[10px] px-2 py-0">
                      {r.rate_per_hr.toFixed(2)}%/hr
                    </Badge>
                  )}
                  {r.status && (
                    <Badge variant={getStatusVariant(r.status)} className="text-[10px] px-2 py-0">
                      {r.status}
                    </Badge>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Tip */}
      <div className="p-2.5 border-t border-slate-800/80 bg-slate-950/60 text-[11px] text-slate-400">
        Tip: Run <code className="text-emerald-400 font-mono bg-slate-900 px-1 py-0.5 rounded">adb bugreport bugreport.zip</code> in your terminal to create bug reports.
      </div>
    </aside>
  );
};
