'use client';

import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
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
  '#14b8a6', // teal-500
  '#6366f1', // indigo-500
];

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface PieChartDataItem {
  name: string;
  value: number;
  color?: string;
}

export interface PieChartProps {
  /** Data items with name, value and optional color */
  data: PieChartDataItem[];
  /** Chart height in pixels (default 320) */
  height?: number;
  /** Inner radius for donut chart (default 0 = full pie) */
  innerRadius?: number;
  /** Outer radius (default 100) */
  outerRadius?: number;
  /** Custom tooltip value formatter */
  valueFormatter?: (value: number) => string;
  /** Show legend (default true) */
  showLegend?: boolean;
  /** Show labels on slices (default false) */
  showLabels?: boolean;
  /** Title displayed in the center of a donut chart */
  centerLabel?: string;
  /** Subtitle displayed below centerLabel */
  centerValue?: string;
}

/* ------------------------------------------------------------------ */
/*  Custom tooltip                                                     */
/* ------------------------------------------------------------------ */

function CustomTooltip({
  active,
  payload,
  valueFormatter,
  total,
}: TooltipProps<number, string> & { valueFormatter?: (v: number) => string; total: number }) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  const value = entry.value ?? 0;
  const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-lg">
      <div className="flex items-center gap-2 text-sm">
        <span
          className="inline-block w-2.5 h-2.5 rounded-sm"
          style={{ backgroundColor: entry.payload?.fill || entry.color }}
        />
        <span className="text-gray-600">{entry.name}:</span>
        <span className="font-semibold text-gray-900">
          {valueFormatter ? valueFormatter(value) : value}
        </span>
        <span className="text-xs text-gray-400">({percentage}%)</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Custom label renderer                                              */
/* ------------------------------------------------------------------ */

interface LabelProps {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  percent: number;
  name: string;
}

function renderCustomLabel({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: LabelProps) {
  if (percent < 0.05) return null; // hide labels for very small slices
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="#fff"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={600}
    >
      {(percent * 100).toFixed(0)}%
    </text>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function PieChart({
  data,
  height = 320,
  innerRadius = 0,
  outerRadius = 100,
  valueFormatter,
  showLegend = true,
  showLabels = false,
  centerLabel,
  centerValue,
}: PieChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          dataKey="value"
          nameKey="name"
          paddingAngle={data.length > 1 ? 2 : 0}
          label={showLabels ? renderCustomLabel : undefined}
          labelLine={false}
          stroke="none"
        >
          {data.map((entry, idx) => (
            <Cell
              key={entry.name}
              fill={entry.color ?? DEFAULT_COLORS[idx % DEFAULT_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip
          content={<CustomTooltip valueFormatter={valueFormatter} total={total} />}
        />
        {showLegend && (
          <Legend
            verticalAlign="bottom"
            align="center"
            iconType="square"
            iconSize={10}
            wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          />
        )}
        {/* Center label for donut charts */}
        {innerRadius > 0 && centerLabel && (
          <text
            x="50%"
            y="50%"
            textAnchor="middle"
            dominantBaseline="central"
          >
            {centerValue && (
              <tspan
                x="50%"
                dy="-8"
                fontSize={20}
                fontWeight={700}
                fill="#111827"
              >
                {centerValue}
              </tspan>
            )}
            <tspan
              x="50%"
              dy={centerValue ? '22' : '0'}
              fontSize={12}
              fill="#6b7280"
            >
              {centerLabel}
            </tspan>
          </text>
        )}
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
