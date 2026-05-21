import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const USD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

/**
 * Stacked series in render order (bottom to top). Each series owns a distinct
 * color so the stacked bar's segments stay visually decodable. Hardware keeps
 * the amber accent (the largest series historically); the long-tail PID 1.3
 * categories sit in muted tones so they read as additive context.
 */
const SERIES = [
  { key: 'hardware', name: 'Hardware', color: '#F59E0B' },           // amber
  { key: 'spares', name: 'Spares', color: '#FBBF24' },               // amber-300
  { key: 'accessories', name: 'Accessories', color: '#FCD34D' },     // amber-200
  { key: 'installation', name: 'Installation', color: '#A78BFA' },   // violet-300
  { key: 'training', name: 'Training', color: '#C4B5FD' },           // violet-200
  { key: 'licensing', name: 'Licensing', color: '#6B7280' },         // slate-500
  { key: 'support', name: 'Support (Y1)', color: '#374151' },        // slate-700
  { key: 'support_recurring', name: 'Support (recurring)', color: '#4B5563' }, // slate-600
  { key: 'adjacent_recurring', name: 'Adjacent recurring', color: '#0EA5E9' }, // sky-500
];

/** Custom tooltip for the stacked bar chart */
function TcoTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="bg-surface border border-[var(--border)] rounded-lg px-4 py-3 text-xs shadow-lg">
      <p className="font-semibold text-text mb-2">Year {label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center justify-between gap-6 py-0.5">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: entry.fill }}
            />
            <span className="text-textMuted capitalize">{entry.name}</span>
          </span>
          <span className="font-mono text-text">{USD.format(entry.value)}</span>
        </div>
      ))}
      <div className="mt-2 pt-2 border-t border-[var(--border)] flex items-center justify-between gap-6">
        <span className="text-textMuted">Total</span>
        <span className="font-mono font-semibold text-accent">
          {USD.format(payload.reduce((sum, e) => sum + (e.value || 0), 0))}
        </span>
      </div>
    </div>
  );
}

/**
 * TcoChart — stacked bar chart of year-by-year costs across every PID 1.3
 * category. Series that are zero across all years are hidden so the legend
 * stays scannable on simple scenarios.
 *
 * @param {Array<{year: number} & Record<string, number>>} data
 */
export default function TcoChart({ data }) {
  // Keep only series that have at least one non-zero value across the model.
  const activeSeries = SERIES.filter((s) =>
    data.some((row) => (row[s.key] ?? 0) > 0)
  );
  // Mark the topmost visible series so we can give it rounded corners.
  const topKey = activeSeries.length > 0 ? activeSeries[activeSeries.length - 1].key : null;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={data}
        margin={{ top: 4, right: 16, bottom: 0, left: 16 }}
        barCategoryGap="28%"
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(232,234,240,0.07)"
          vertical={false}
        />
        <XAxis
          dataKey="year"
          tickFormatter={(v) => `Yr ${v}`}
          tick={{ fill: '#6B7280', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(232,234,240,0.08)' }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v) => {
            if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
            if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
            return `$${v}`;
          }}
          tick={{ fill: '#6B7280', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={64}
        />
        <Tooltip content={<TcoTooltip />} cursor={{ fill: 'rgba(232,234,240,0.04)' }} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: '#6B7280', paddingTop: 12 }}
          formatter={(value) => (
            <span style={{ color: '#6B7280', textTransform: 'capitalize' }}>{value}</span>
          )}
        />
        {activeSeries.map((s) => (
          <Bar
            key={s.key}
            dataKey={s.key}
            name={s.name}
            stackId="a"
            fill={s.color}
            radius={s.key === topKey ? [4, 4, 0, 0] : [0, 0, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
