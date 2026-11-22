import React, { useState } from 'react';
import { Card } from '../ui/Card';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Cell
} from 'recharts';
import { PowerComponent } from '../../types/api';
import { BarChart2, PieChart as PieChartIcon } from 'lucide-react';

interface TopConsumersChartProps {
  consumers: PowerComponent[];
}

const COLORS = [
  '#ef4444',
  '#f97316',
  '#f59e0b',
  '#6366f1',
  '#8b5cf6',
  '#3b82f6',
  '#10b981',
  '#14b8a6'
];

export const TopConsumersChart: React.FC<TopConsumersChartProps> = ({ consumers }) => {
  const [chartType, setChartType] = useState<'bar' | 'pie'>('bar');

  if (!consumers || consumers.length === 0) {
    return (
      <Card className="p-6 text-center text-slate-400 text-sm">
        No power drain subsystem breakdown available.
      </Card>
    );
  }

  const topItems = consumers.slice(0, 8).map((c) => ({
    ...c,
    mahRounded: Math.round((c.mah || 0) * 10) / 10
  }));

  return (
    <Card className="p-4 flex flex-col h-[340px]">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-200">Top Energy Drainers (mAh)</h3>
          <span className="text-xs text-slate-500">({topItems.length})</span>
        </div>

        {/* Inline Bar / Pie Chart Toggle */}
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setChartType('bar')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
              chartType === 'bar'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart2 className="w-3 h-3" />
            <span>Bar Chart</span>
          </button>
          <button
            type="button"
            onClick={() => setChartType('pie')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
              chartType === 'pie'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <PieChartIcon className="w-3 h-3" />
            <span>Pie Chart</span>
          </button>
        </div>
      </div>

      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' ? (
            <BarChart
              data={topItems}
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
                tickFormatter={(val: string) =>
                  val && val.length > 14 ? `${val.slice(0, 12)}…` : val || ''
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  color: '#f8fafc'
                }}
                itemStyle={{ color: '#f1f5f9' }}
                labelStyle={{ color: '#94a3b8' }}
                formatter={(val: any) => [`${val} mAh`, 'Drain']}
              />
              <Bar dataKey="mahRounded" radius={[0, 4, 4, 0]}>
                {topItems.map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          ) : (
            <PieChart>
              <Pie
                data={topItems}
                dataKey="mahRounded"
                nameKey="component"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {topItems.map((_entry, index) => (
                  <Cell key={`pie-cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  color: '#f8fafc'
                }}
                itemStyle={{ color: '#f1f5f9' }}
                labelStyle={{ color: '#94a3b8' }}
                formatter={(val: any) => [`${val} mAh`, 'Drain']}
              />
              <Legend
                wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }}
                formatter={(value: string) =>
                  value && value.length > 18 ? `${value.slice(0, 16)}…` : value
                }
              />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
