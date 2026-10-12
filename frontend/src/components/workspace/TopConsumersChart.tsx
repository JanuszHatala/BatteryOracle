import React from 'react';
import { Card } from '../ui/Card';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell
} from 'recharts';
import { PowerComponent } from '../../types/api';

interface TopConsumersChartProps {
  consumers: PowerComponent[];
}

const COLORS = ['#ef4444', '#f97316', '#f59e0b', '#6366f1', '#8b5cf6', '#3b82f6'];

export const TopConsumersChart: React.FC<TopConsumersChartProps> = ({ consumers }) => {
  if (!consumers || consumers.length === 0) {
    return (
      <Card className="p-6 text-center text-slate-400 text-sm">
        No power drain subsystem breakdown available.
      </Card>
    );
  }

  const top10 = consumers.slice(0, 8);

  return (
    <Card className="p-4 flex flex-col h-[340px]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-200">Top Energy Drainers (mAh)</h3>
        <span className="text-xs text-slate-400">Top {top10.length} subsystems</span>
      </div>

      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={top10}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
          >
            <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} unit=" mAh" />
            <YAxis
              type="category"
              dataKey="component"
              stroke="#94a3b8"
              fontSize={11}
              tickLine={false}
              width={110}
              tickFormatter={(val: string) => (val && val.length > 14 ? `${val.slice(0, 12)}…` : val || '')}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '0.5rem',
                fontSize: '12px',
                color: '#f8fafc'
              }}
              formatter={(val: any) => [`${Math.round(val)} mAh`, 'Drain']}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="mah" radius={[0, 4, 4, 0]}>
              {top10.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
