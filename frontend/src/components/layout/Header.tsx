import React from 'react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Zap, Upload, Settings as SettingsIcon, GitCompare, RefreshCw } from 'lucide-react';
import { Settings } from '../../types/api';

interface HeaderProps {
  settings: Settings | null;
  onOpenUpload: () => void;
  onOpenSettings: () => void;
  isComparativeMode: boolean;
  onToggleComparativeMode: () => void;
  selectedCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  settings,
  onOpenUpload,
  onOpenSettings,
  isComparativeMode,
  onToggleComparativeMode,
  selectedCount
}) => {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-4 flex items-center justify-between shrink-0 select-none z-20">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-950">
          <Zap className="w-4 h-4" />
        </div>
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-100 text-sm tracking-tight">BatteryOracle</span>
          <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60">2.0</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {settings && (
          <div className="hidden md:flex items-center gap-2">
            <Badge variant="scope" className="font-mono text-[11px] px-2 py-0.5">
              {settings.active_llm_model}
            </Badge>
          </div>
        )}

        <Button
          variant={isComparativeMode ? 'primary' : 'secondary'}
          size="sm"
          onClick={onToggleComparativeMode}
          className="text-xs"
        >
          <GitCompare className="w-3.5 h-3.5" />
          <span>Compare {selectedCount > 0 ? `(${selectedCount})` : ''}</span>
        </Button>

        <Button
          variant="primary"
          size="sm"
          onClick={onOpenUpload}
          className="text-xs bg-emerald-600 hover:bg-emerald-500"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload Bugreport</span>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenSettings}
          className="p-2 text-slate-400 hover:text-slate-100"
          title="Settings"
        >
          <SettingsIcon className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
};
