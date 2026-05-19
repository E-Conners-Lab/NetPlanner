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
 * TcoChart — stacked bar chart of year-by-year hardware / licensing / support costs.
 *
 * @param {{ year: number, hardware: number, licensing: number, support: number }[]} data
 */
export default function TcoChart({ data }) {
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
        {/* Amber (primary) for hardware — typically the largest series */}
        <Bar dataKey="hardware" name="Hardware" stackId="a" fill="#F59E0B" radius={[0, 0, 0, 0]} />
        {/* Slate tones for the OpEx series */}
        <Bar dataKey="licensing" name="Licensing" stackId="a" fill="#6B7280" radius={[0, 0, 0, 0]} />
        <Bar dataKey="support" name="Support" stackId="a" fill="#374151" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
