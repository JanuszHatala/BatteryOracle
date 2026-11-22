import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { KpiMetrics, PowerComponent } from '../../types/api';
import { Battery, Zap, Clock, ShieldAlert, Cpu } from 'lucide-react';

interface KpiGridProps {
  kpis: KpiMetrics;
  topConsumer?: PowerComponent | null;
}

export const KpiGrid: React.FC<KpiGridProps> = ({ kpis, topConsumer }) => {
  const drainRate = kpis.rate_per_hr ?? 0;
  const drainSpeedClass =
    drainRate <= 1.0
      ? { variant: 'optimal' as const, label: 'Optimal' }
      : drainRate <= 2.5
      ? { variant: 'elevated' as const, label: 'Elevated' }
      : { variant: 'severe' as const, label: 'Severe Drain' };

  const durationHours = kpis.duration_hrs.toFixed(1);
  const totalDrainPct = kpis.drop_pct ?? 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      {/* KPI 1: Drain Rate */}
      <Card className="p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
          <span className="font-medium">Drain Rate</span>
          <Zap className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div>
          <div className="text-xl font-bold text-slate-100">
            {drainRate.toFixed(2)}
            <span className="text-xs font-normal text-slate-400 ml-1">%/hr</span>
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            <Badge variant={drainSpeedClass.variant}>
              {drainSpeedClass.label}
            </Badge>
          </div>
        </div>
      </Card>

      {/* KPI 2: Total Drain */}
      <Card className="p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
          <span className="font-medium">Total Drain</span>
          <Battery className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div>
          <div className="text-xl font-bold text-slate-100">
            {totalDrainPct.toFixed(1)}
            <span className="text-xs font-normal text-slate-400 ml-1">%</span>
          </div>
          <div className="mt-1 text-xs text-slate-400 truncate">
            {kpis.start_level}% → {kpis.end_level}%
          </div>
        </div>
      </Card>

      {/* KPI 3: Observed Time */}
      <Card className="p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
          <span className="font-medium">Observed Time</span>
          <Clock className="w-3.5 h-3.5 text-blue-400" />
        </div>
        <div>
          <div className="text-xl font-bold text-slate-100">
            {durationHours}
            <span className="text-xs font-normal text-slate-400 ml-1">hrs</span>
          </div>
          <div className="mt-1 text-xs text-slate-400 truncate">
            {kpis.status || 'Complete timeline'}
          </div>
        </div>
      </Card>

      {/* KPI 4: Time Boundaries */}
      <Card className="p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
          <span className="font-medium">Clamp Window</span>
          <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-200 truncate">
            {kpis.start_time ? kpis.start_time.split(' ')[1] || kpis.start_time : '00:00'}
            <span className="mx-1 text-slate-500">→</span>
            {kpis.end_time ? kpis.end_time.split(' ')[1] || kpis.end_time : '00:00'}
          </div>
          <div className="mt-1 text-xs text-slate-400 truncate">
            {kpis.start_time ? kpis.start_time.split(' ')[0] : ''}
          </div>
        </div>
      </Card>

      {/* KPI 5: Top Offender */}
      <Card className="p-3.5 flex flex-col justify-between col-span-2 sm:col-span-1">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
          <span className="font-medium">Top Offender</span>
          <Cpu className="w-3.5 h-3.5 text-rose-400" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-100 truncate" title={topConsumer?.component ?? 'None'}>
            {topConsumer ? topConsumer.component : 'None detected'}
          </div>
          <div className="mt-1 text-xs text-slate-400">
            {topConsumer ? `${Math.round(topConsumer.mah)} mAh` : 'No drain data'}
          </div>
        </div>
      </Card>
    </div>
  );
};
