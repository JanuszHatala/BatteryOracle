import React, { useMemo, useState } from 'react';
import { Card } from '../ui/Card';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea
} from 'recharts';

interface DischargePoint {
  timestamp: string | number;
  battery_level: number;
  is_screen_on?: boolean;
}

interface DischargeChartProps {
  data: DischargePoint[];
  title?: string;
  nightStartHour?: number;
  nightEndHour?: number;
}

export const DischargeChart: React.FC<DischargeChartProps> = ({
  data,
  title = 'Discharge Curve & Timeline',
  nightStartHour = 23,
  nightEndHour = 7
}) => {
  const [showNightShading, setShowNightShading] = useState(true);

  // Format timestamps and detect night / screen-off periods for shading
  const formattedData = useMemo(() => {
    return data.map((item, idx) => {
      let label = `${idx}`;
      let hour: number | null = null;
      if (typeof item.timestamp === 'string') {
        const d = new Date(item.timestamp);
        if (!isNaN(d.getTime())) {
          label = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          hour = d.getHours();
        } else {
          label = item.timestamp;
          const m = item.timestamp.match(/(\d{1,2}):\d{2}/);
          if (m) hour = parseInt(m[1], 10);
        }
      } else if (typeof item.timestamp === 'number') {
        const ms = item.timestamp > 1e11 ? item.timestamp : item.timestamp * 1000;
        const d = new Date(ms);
        label = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        hour = d.getHours();
      }

      let isNightWindow = false;
      if (hour !== null) {
        if (nightStartHour > nightEndHour) {
          isNightWindow = hour >= nightStartHour || hour < nightEndHour;
        } else {
          isNightWindow = hour >= nightStartHour && hour < nightEndHour;
        }
      }

      return {
        ...item,
        timeLabel: label,
        isNightOrScreenOff: isNightWindow || item.is_screen_on === false
      };
    });
  }, [data, nightStartHour, nightEndHour]);

  // Find intervals to shade when showNightShading is enabled
  const shadedBands = useMemo(() => {
    const bands: { start: string; end: string }[] = [];
    let currentStart: string | null = null;

    formattedData.forEach((pt) => {
      if (pt.isNightOrScreenOff && !currentStart) {
        currentStart = pt.timeLabel;
      } else if (!pt.isNightOrScreenOff && currentStart) {
        bands.push({ start: currentStart, end: pt.timeLabel });
        currentStart = null;
      }
    });

    if (currentStart && formattedData.length > 0) {
      bands.push({ start: currentStart, end: formattedData[formattedData.length - 1].timeLabel });
    }

    return bands;
  }, [formattedData]);

  if (!data || data.length === 0) {
    return (
      <Card className="p-6 text-center text-slate-400 text-sm">
        No discharge curve telemetry available for this report.
      </Card>
    );
  }

  return (
    <Card className="p-4 flex flex-col h-[340px]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-indigo-400 inline-block rounded" />
            Battery %
          </span>
          <label className="flex items-center gap-1.5 cursor-pointer select-none hover:text-slate-200 transition-colors bg-slate-900/80 border border-slate-800 px-2 py-0.5 rounded-md">
            <input
              type="checkbox"
              checked={showNightShading}
              onChange={(e) => setShowNightShading(e.target.checked)}
              className="rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-indigo-500 w-3 h-3"
            />
            <span>Show 🌙 Night Shading</span>
          </label>
        </div>
      </div>

      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
            <XAxis
              dataKey="timeLabel"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              domain={[0, 100]}
              tickLine={false}
              unit="%"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '0.5rem',
                fontSize: '12px',
                color: '#f8fafc'
              }}
              formatter={(val: any) => [`${val}%`, 'Battery Level']}
              labelStyle={{ color: '#94a3b8' }}
            />
            {showNightShading &&
              shadedBands.map((band, idx) => (
                <ReferenceArea
                  key={idx}
                  x1={band.start}
                  x2={band.end}
                  fill="#1e1b4b"
                  fillOpacity={0.45}
                />
              ))}
            <Line
              type="monotone"
              dataKey="battery_level"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#818cf8' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
