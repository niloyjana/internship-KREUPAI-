'use client';

import {
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from 'recharts';

/* ------------------------------------------------------------------ */
/*  Color palette (Tailwind-aligned)                                   */
/* ------------------------------------------------------------------ */

const DEFAULT_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#06b6d4', // cyan-500
  '#f97316', // orange-500
  '#ec4899', // pink-500
];

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface AreaChartSeries {
  /** The data key in each record to plot */
  dataKey: string;
  /** Human-readable label for the legend / tooltip */
  label: string;
  /** Optional colour override (hex) */
  color?: string;
  /** Fill opacity for the area (default 0.15) */
  fillOpacity?: number;
  /** Stack ID to stack areas together */
  stackId?: string;
}

export interface AreaChartProps<T extends Record<string, unknown>> {
  /** The data array to render */
  data: T[];
  /** The key used for the X-axis category */
  xAxisKey: string;
  /** One or more area series to render */
  series: AreaChartSeries[];
  /** Chart height in pixels (default 320) */
  height?: number;
  /** X-axis label */
  xAxisLabel?: string;
  /** Y-axis label */
  yAxisLabel?: string;
  /** Custom tooltip value formatter */
  valueFormatter?: (value: number) => string;
  /** Show grid lines (default true) */
  showGrid?: boolean;
  /** Show legend (default true) */
  showLegend?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Custom tooltip                                                     */
/* ------------------------------------------------------------------ */

function CustomTooltip({
  active,
  payload,
  label,
  valueFormatter,
}: TooltipProps<number, string> & { valueFormatter?: (v: number) => string }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-lg">
      <p className="text-xs font-medium text-gray-500 mb-1.5">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 text-sm">
          <span
            className="inline-block w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-semibold text-gray-900">
            {valueFormatter ? valueFormatter(entry.value ?? 0) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function AreaChart<T extends Record<string, unknown>>({
  data,
  xAxisKey,
  series,
  height = 320,
  xAxisLabel,
  yAxisLabel,
  valueFormatter,
  showGrid = true,
  showLegend = true,
}: AreaChartProps<T>) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsAreaChart
        data={data}
        margin={{ top: 8, right: 16, left: yAxisLabel ? 12 : 0, bottom: xAxisLabel ? 20 : 4 }}
      >
        <defs>
          {series.map((s, idx) => {
            const color = s.color ?? DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
            return (
              <linearGradient
                key={s.dataKey}
                id={`gradient-${s.dataKey}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            );
          })}
        </defs>
        {showGrid && (
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        )}
        <XAxis
          dataKey={xAxisKey}
          tick={{ fontSize: 12, fill: '#6b7280' }}
          axisLine={{ stroke: '#e5e7eb' }}
          tickLine={false}
          label={
            xAxisLabel
              ? { value: xAxisLabel, position: 'insideBottom', offset: -12, fontSize: 12, fill: '#9ca3af' }
              : undefined
          }
        />
        <YAxis
          tick={{ fontSize: 12, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          label={
            yAxisLabel
              ? { value: yAxisLabel, angle: -90, position: 'insideLeft', offset: 4, fontSize: 12, fill: '#9ca3af' }
              : undefined
          }
        />
        <Tooltip
          content={<CustomTooltip valueFormatter={valueFormatter} />}
        />
        {showLegend && (
          <Legend
            verticalAlign="top"
            align="right"
            iconType="square"
            iconSize={10}
            wrapperStyle={{ fontSize: 12, paddingBottom: 8 }}
          />
        )}
        {series.map((s, idx) => {
          const color = s.color ?? DEFAULT_COLORS[idx % DEFAULT_COLORS.length];
          return (
            <Area
              key={s.dataKey}
              type="monotone"
              dataKey={s.dataKey}
              name={s.label}
              stroke={color}
              strokeWidth={2}
              fill={`url(#gradient-${s.dataKey})`}
              fillOpacity={1}
              stackId={s.stackId}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2 }}
            />
          );
        })}
      </RechartsAreaChart>
    </ResponsiveContainer>
  );
}
