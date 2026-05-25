import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Card from '../ui/Card.jsx';

const USD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const SIGNED_USD = (n) => {
  if (n === 0) return USD.format(0);
  const formatted = USD.format(Math.abs(n));
  return n > 0 ? `+${formatted}` : `−${formatted}`;
};

/** Inputs that the diff treats as comparable scalars. */
const SCALAR_INPUT_FIELDS = [
  { key: 'device_count', label: 'Device count' },
  { key: 'hardware_cost_per_unit', label: 'Hardware $ / unit' },
  { key: 'licensing_cost_per_unit_year', label: 'Licensing $ / unit / year' },
  { key: 'support_cost_year_one', label: 'Support Y1 ($)' },
  { key: 'lifecycle_years', label: 'Lifecycle years' },
  { key: 'installation_cost', label: 'Installation ($)' },
  { key: 'accessories_cost_per_unit', label: 'Accessories $ / unit' },
  { key: 'spares_percent', label: 'Spares (%)' },
  { key: 'training_cost', label: 'Training ($)' },
  { key: 'support_cost_recurring_per_year', label: 'Support recurring / year ($)' },
  { key: 'adjacent_recurring_cost_per_year', label: 'Adjacent recurring / year ($)' },
];

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Build an array of refresh-event strings for diffing. */
function refreshEventLines(inputs) {
  const events = inputs?.refresh_events ?? [];
  return events
    .map(
      (e) =>
        `Y${e.year}: ${e.percent_of_devices}%${
          e.cost_per_unit_override != null ? ` @ $${e.cost_per_unit_override}/unit` : ''
        }`,
    )
    .sort();
}

function shortLabel(scenario) {
  if (!scenario) return '';
  return `${scenario.scenario_name} · v${scenario.version ?? 1}`;
}

function ScenarioPicker({ id, label, scenarios, value, onChange, excludeId }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-textMuted">
        {label}
      </label>
      <select
        id={id}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className={[
          'w-full rounded-md px-3 py-2 text-sm bg-bg text-text',
          'border border-[var(--border)] transition-colors duration-150',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
          'focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
          'hover:border-textMuted/40',
        ].join(' ')}
      >
        <option value="">— Select a scenario —</option>
        {scenarios
          .filter((s) => s.id !== excludeId)
          .map((s) => (
            <option key={s.id} value={s.id}>
              {shortLabel(s)} · {USD.format(s.total_5yr)}
            </option>
          ))}
      </select>
    </div>
  );
}

/** Overlay line chart: both scenarios' year-by-year totals on shared axes. */
function CompareChart({ a, b }) {
  // Merge the two breakdowns by year so the chart has one row per year.
  const yearsA = a.year_by_year ?? [];
  const yearsB = b.year_by_year ?? [];
  const allYears = Array.from(
    new Set([...yearsA.map((y) => y.year), ...yearsB.map((y) => y.year)]),
  ).sort((x, y) => x - y);

  const data = allYears.map((year) => ({
    year,
    a: yearsA.find((y) => y.year === year)?.total ?? null,
    b: yearsB.find((y) => y.year === year)?.total ?? null,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(232,234,240,0.07)" vertical={false} />
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
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value, name) => [USD.format(value ?? 0), name]}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#6B7280', paddingTop: 12 }} />
        <Line type="monotone" dataKey="a" name={shortLabel(a)} stroke="#F59E0B" strokeWidth={2} dot />
        <Line type="monotone" dataKey="b" name={shortLabel(b)} stroke="#0EA5E9" strokeWidth={2} dot />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Per-year side-by-side table with delta column. */
function CompareTable({ a, b }) {
  const yearsA = a.year_by_year ?? [];
  const yearsB = b.year_by_year ?? [];
  const allYears = Array.from(
    new Set([...yearsA.map((y) => y.year), ...yearsB.map((y) => y.year)]),
  ).sort((x, y) => x - y);

  const totalA = a.total_5yr ?? 0;
  const totalB = b.total_5yr ?? 0;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className="py-2 text-xs font-semibold text-textMuted text-left pl-0 pr-4">Year</th>
            <th className="py-2 text-xs font-semibold text-textMuted text-right px-3">
              {shortLabel(a)}
            </th>
            <th className="py-2 text-xs font-semibold text-textMuted text-right px-3">
              {shortLabel(b)}
            </th>
            <th className="py-2 text-xs font-semibold text-textMuted text-right px-3">Delta (B−A)</th>
          </tr>
        </thead>
        <tbody>
          {allYears.map((year) => {
            const va = yearsA.find((y) => y.year === year)?.total ?? 0;
            const vb = yearsB.find((y) => y.year === year)?.total ?? 0;
            const delta = vb - va;
            return (
              <tr key={year} className="border-b border-[var(--border)]/50">
                <td className="py-2 pr-4 font-medium text-text">Year {year}</td>
                <td className="py-2 px-3 text-right font-mono text-textMuted tabular-nums">
                  {USD.format(va)}
                </td>
                <td className="py-2 px-3 text-right font-mono text-textMuted tabular-nums">
                  {USD.format(vb)}
                </td>
                <td
                  className={[
                    'py-2 px-3 text-right font-mono tabular-nums',
                    delta > 0 ? 'text-red-300' : delta < 0 ? 'text-emerald-300' : 'text-textMuted',
                  ].join(' ')}
                >
                  {SIGNED_USD(delta)}
                </td>
              </tr>
            );
          })}
          <tr className="border-t-2 border-[var(--border)]">
            <td className="py-2 pr-4 font-semibold text-text">5-year total</td>
            <td className="py-2 px-3 text-right font-mono font-semibold text-text tabular-nums">
              {USD.format(totalA)}
            </td>
            <td className="py-2 px-3 text-right font-mono font-semibold text-text tabular-nums">
              {USD.format(totalB)}
            </td>
            <td
              className={[
                'py-2 px-3 text-right font-mono font-semibold tabular-nums',
                totalB - totalA > 0 ? 'text-red-400' : totalB - totalA < 0 ? 'text-emerald-400' : 'text-textMuted',
              ].join(' ')}
            >
              {SIGNED_USD(totalB - totalA)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/** Diff inputs and refresh events between the two scenarios. */
function CompareAssumptions({ a, b }) {
  const inputsA = a.inputs ?? {};
  const inputsB = b.inputs ?? {};

  const scalarDiffs = SCALAR_INPUT_FIELDS.filter(({ key }) => {
    const va = inputsA[key] ?? 0;
    const vb = inputsB[key] ?? 0;
    return Number(va) !== Number(vb);
  });

  const refreshA = refreshEventLines(inputsA).join('\n');
  const refreshB = refreshEventLines(inputsB).join('\n');
  const refreshChanged = refreshA !== refreshB;

  if (scalarDiffs.length === 0 && !refreshChanged) {
    return (
      <p className="text-xs text-textMuted">
        Inputs and refresh events are identical between these two scenarios.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {scalarDiffs.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="py-2 text-xs font-semibold text-textMuted text-left pl-0 pr-4">
                  Input
                </th>
                <th className="py-2 text-xs font-semibold text-textMuted text-right px-3">
                  {shortLabel(a)}
                </th>
                <th className="py-2 text-xs font-semibold text-textMuted text-right px-3">
                  {shortLabel(b)}
                </th>
              </tr>
            </thead>
            <tbody>
              {scalarDiffs.map(({ key, label }) => (
                <tr key={key} className="border-b border-[var(--border)]/50">
                  <td className="py-2 pr-4 text-text">{label}</td>
                  <td className="py-2 px-3 text-right font-mono text-textMuted tabular-nums">
                    {inputsA[key] ?? 0}
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-text tabular-nums">
                    {inputsB[key] ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {refreshChanged && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <p className="text-xs font-semibold text-textMuted mb-1">{shortLabel(a)} refresh events</p>
            {refreshEventLines(inputsA).length === 0 ? (
              <p className="text-xs text-textMuted/60">None</p>
            ) : (
              <ul className="text-xs text-text font-mono space-y-0.5">
                {refreshEventLines(inputsA).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-textMuted mb-1">{shortLabel(b)} refresh events</p>
            {refreshEventLines(inputsB).length === 0 ? (
              <p className="text-xs text-textMuted/60">None</p>
            ) : (
              <ul className="text-xs text-text font-mono space-y-0.5">
                {refreshEventLines(inputsB).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * TcoCompare — screen-first side-by-side comparison of two saved scenarios
 * (PID amendment 1.5). Pure read-only view over data the saved-scenarios list
 * already carries — no extra API call required.
 *
 * @param {object[]} scenarios — saved TCOScenarioRead[] for the current project
 */
export default function TcoCompare({ scenarios }) {
  const [aId, setAId] = useState(null);
  const [bId, setBId] = useState(null);

  const a = useMemo(() => scenarios.find((s) => s.id === aId) ?? null, [scenarios, aId]);
  const b = useMemo(() => scenarios.find((s) => s.id === bId) ?? null, [scenarios, bId]);

  // The screen layout. If fewer than 2 scenarios exist there is nothing to
  // compare — render a hint instead of empty pickers.
  if (!Array.isArray(scenarios) || scenarios.length < 2) {
    return (
      <Card title="Compare Scenarios">
        <p className="text-sm text-textMuted">
          Save at least two scenarios (or two versions of one scenario) to compare them here.
        </p>
      </Card>
    );
  }

  return (
    <Card title="Compare Scenarios">
      <div className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ScenarioPicker
            id="compare-a"
            label="Scenario A"
            scenarios={scenarios}
            value={aId}
            onChange={setAId}
            excludeId={bId}
          />
          <ScenarioPicker
            id="compare-b"
            label="Scenario B"
            scenarios={scenarios}
            value={bId}
            onChange={setBId}
            excludeId={aId}
          />
        </div>

        {a && b && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="rounded-lg border border-[var(--border)] p-3">
                <p className="text-xs uppercase tracking-wide font-semibold text-textMuted mb-1">
                  Scenario A
                </p>
                <p className="text-sm text-text font-medium">{shortLabel(a)}</p>
                <p className="text-xs text-textMuted">
                  Saved {formatDate(a.created_at)} ·{' '}
                  <span className="font-mono text-accent">{USD.format(a.total_5yr)}</span>
                </p>
              </div>
              <div className="rounded-lg border border-[var(--border)] p-3">
                <p className="text-xs uppercase tracking-wide font-semibold text-textMuted mb-1">
                  Scenario B
                </p>
                <p className="text-sm text-text font-medium">{shortLabel(b)}</p>
                <p className="text-xs text-textMuted">
                  Saved {formatDate(b.created_at)} ·{' '}
                  <span className="font-mono text-accent">{USD.format(b.total_5yr)}</span>
                </p>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-textMuted mb-2">Year-by-year totals</p>
              <CompareChart a={a} b={b} />
            </div>

            <div>
              <p className="text-xs font-semibold text-textMuted mb-2">Per-year breakdown</p>
              <CompareTable a={a} b={b} />
            </div>

            <div>
              <p className="text-xs font-semibold text-textMuted mb-2">Assumption diff</p>
              <CompareAssumptions a={a} b={b} />
            </div>
          </div>
        )}

        {(!a || !b) && (
          <p className="text-xs text-textMuted">
            Pick two scenarios above to see a side-by-side comparison.
          </p>
        )}
      </div>
    </Card>
  );
}
