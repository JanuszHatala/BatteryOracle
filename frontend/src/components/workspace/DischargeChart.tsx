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
  customNightStart?: string | null;
  customNightEnd?: string | null;
}

export const DischargeChart: React.FC<DischargeChartProps> = ({
  data,
  title = 'Discharge Curve & Timeline',
  nightStartHour = 23,
  nightEndHour = 7,
  customNightStart,
  customNightEnd
}) => {
  const [showNightShading, setShowNightShading] = useState(true);

  const customBoundsMs = useMemo(() => {
    if (!customNightStart || !customNightEnd) return null;
    const s = new Date(customNightStart).getTime();
    const e = new Date(customNightEnd).getTime();
    if (isNaN(s) || isNaN(e)) return null;
    return { startMs: s, endMs: e };
  }, [customNightStart, customNightEnd]);

  // Determine whether timeline spans multiple calendar days
  const spansMultipleDays = useMemo(() => {
    if (data.length < 2) return false;
    const first = new Date(data[0].timestamp);
    const last = new Date(data[data.length - 1].timestamp);
    if (isNaN(first.getTime()) || isNaN(last.getTime())) return false;
    return (
      first.toDateString() !== last.toDateString() ||
      last.getTime() - first.getTime() > 18 * 3600 * 1000
    );
  }, [data]);

  // Format timestamps with unique point index so ReferenceArea works across multi-day timelines
  const formattedData = useMemo(() => {
    return data.map((item, idx) => {
      let displayLabel = `${idx}`;
      let fullLabel = `${item.timestamp}`;
      let hour: number | null = null;
      let pointMs: number | null = null;

      if (typeof item.timestamp === 'string') {
        const d = new Date(item.timestamp);
        if (!isNaN(d.getTime())) {
          pointMs = d.getTime();
          hour = d.getHours();
          const hhmm = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
          const mmdd = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
          displayLabel = spansMultipleDays ? `${mmdd} ${hhmm}` : hhmm;
          fullLabel = `${d.getFullYear()}-${mmdd} ${hhmm}`;
        } else {
          displayLabel = item.timestamp;
          fullLabel = item.timestamp;
          const m = item.timestamp.match(/(\d{1,2}):\d{2}/);
          if (m) hour = parseInt(m[1], 10);
        }
      } else if (typeof item.timestamp === 'number') {
        const ms = item.timestamp > 1e11 ? item.timestamp : item.timestamp * 1000;
        const d = new Date(ms);
        pointMs = d.getTime();
        hour = d.getHours();
        const hhmm = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
        const mmdd = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        displayLabel = spansMultipleDays ? `${mmdd} ${hhmm}` : hhmm;
        fullLabel = `${d.getFullYear()}-${mmdd} ${hhmm}`;
      }

      let isNightWindow = false;
      if (customBoundsMs && pointMs !== null && pointMs >= customBoundsMs.startMs && pointMs <= customBoundsMs.endMs) {
        isNightWindow = true;
      } else if (hour !== null) {
        if (nightStartHour > nightEndHour) {
          isNightWindow = hour >= nightStartHour || hour < nightEndHour;
        } else if (nightStartHour < nightEndHour) {
          isNightWindow = hour >= nightStartHour && hour < nightEndHour;
        }
      }

      return {
        ...item,
        idx,
        displayLabel,
        fullLabel,
        isNightWindow
      };
    });
  }, [data, nightStartHour, nightEndHour, customBoundsMs, spansMultipleDays]);

  // Find contiguous night intervals by unique point index
  const shadedBands = useMemo(() => {
    const bands: { startIdx: number; endIdx: number }[] = [];
    let currentStartIdx: number | null = null;

    formattedData.forEach((pt, i) => {
      if (pt.isNightWindow && currentStartIdx === null) {
        currentStartIdx = i;
      } else if (!pt.isNightWindow && currentStartIdx !== null) {
        bands.push({ startIdx: currentStartIdx, endIdx: i });
        currentStartIdx = null;
      }
    });

    if (currentStartIdx !== null && formattedData.length > 0) {
      bands.push({ startIdx: currentStartIdx, endIdx: formattedData.length - 1 });
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

  const nightHoursText = `${String(nightStartHour).padStart(2, '0')}:00–${String(nightEndHour).padStart(2, '0')}:00`;

  return (
    <Card className="p-4 flex flex-col h-[340px]">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-indigo-400 inline-block rounded" />
            Battery %
          </span>
          {showNightShading && (
            <span className="flex items-center gap-1.5 text-indigo-300/90">
              <span className="w-3 h-2.5 rounded-sm bg-indigo-500/35 border border-indigo-400/50 inline-block" />
              Night ({nightHoursText})
            </span>
          )}
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
              dataKey="idx"
              type="number"
              domain={[0, Math.max(0, formattedData.length - 1)]}
              tickFormatter={(idx: number) => formattedData[Math.round(idx)]?.displayLabel || ''}
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              minTickGap={28}
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
              labelFormatter={(idx: any) => {
                const pt = formattedData[Number(idx)];
                if (!pt) return '';
                return `${pt.fullLabel}${pt.isNightWindow ? ' (🌙 Night Window)' : ' (☀️ Daytime)'}`;
              }}
              formatter={(val: any) => [`${val}%`, 'Battery Level']}
              labelStyle={{ color: '#94a3b8', marginBottom: '4px' }}
            />
            {showNightShading &&
              shadedBands.map((band, idx) => (
                <ReferenceArea
                  key={idx}
                  x1={band.startIdx}
                  x2={band.endIdx}
                  fill="#6366f1"
                  fillOpacity={0.22}
                  stroke="#818cf8"
                  strokeOpacity={0.45}
                  strokeDasharray="3 3"
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
