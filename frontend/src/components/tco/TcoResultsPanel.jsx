import { useState } from 'react';
import Card from '../ui/Card.jsx';
import Button from '../ui/Button.jsx';
import TcoChart from './TcoChart.jsx';

const USD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

/**
 * Year-by-year cost breakdown columns. Order matches the chart stack (bottom-up)
 * so the table reads consistently with the visual. Columns are hidden when the
 * series is zero across every year — simple scenarios stay readable.
 */
const COLUMNS = [
  { key: 'hardware', label: 'Hardware' },
  { key: 'spares', label: 'Spares' },
  { key: 'accessories', label: 'Accessories' },
  { key: 'installation', label: 'Installation' },
  { key: 'training', label: 'Training' },
  { key: 'licensing', label: 'Licensing' },
  { key: 'support', label: 'Support (Y1)' },
  { key: 'support_recurring', label: 'Support (recurring)' },
  { key: 'adjacent_recurring', label: 'Adjacent recurring' },
];

/** Year-by-year cost breakdown table */
function YearByYearTable({ rows }) {
  const activeColumns = COLUMNS.filter((col) =>
    rows.some((row) => (row[col.key] ?? 0) > 0)
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className="py-2 text-xs font-semibold text-textMuted text-left pl-0 pr-4">
              Year
            </th>
            {activeColumns.map((col) => (
              <th
                key={col.key}
                className="py-2 text-xs font-semibold text-textMuted text-right px-3 whitespace-nowrap"
              >
                {col.label}
              </th>
            ))}
            <th className="py-2 text-xs font-semibold text-textMuted text-right px-3">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year} className="border-b border-[var(--border)]/50">
              <td className="py-2 pr-4 font-medium text-text">Year {row.year}</td>
              {activeColumns.map((col) => (
                <td
                  key={col.key}
                  className="py-2 px-3 text-right font-mono text-textMuted tabular-nums"
                >
                  {USD.format(row[col.key] ?? 0)}
                </td>
              ))}
              <td className="py-2 px-3 text-right font-mono font-semibold text-text tabular-nums">
                {USD.format(row.total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Prominent 5-year total display */
function TotalBadge({ total }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-accent/10 border border-accent/20 px-5 py-4">
      <span className="text-sm font-medium text-textMuted">
        Total Cost of Ownership
      </span>
      <span className="text-2xl font-semibold font-mono text-accent tabular-nums">
        {USD.format(total)}
      </span>
    </div>
  );
}

/** Warning banner shown when the backend returns warnings */
function WarningsBanner({ warnings }) {
  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/8 px-4 py-3">
      <div className="flex items-start gap-3">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-amber-400 mt-0.5 shrink-0"
          aria-hidden="true"
        >
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
          <path d="M12 9v4" />
          <path d="M12 17h.01" />
        </svg>
        <div>
          <p className="text-xs font-semibold text-amber-400 mb-1">Review before saving</p>
          <ul className="space-y-1">
            {warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-300/90">
                {w}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

/**
 * TcoResultsPanel — displays the preview result and the Save CTA.
 *
 * @param {object}   result      — TCOResult from previewTco
 * @param {boolean}  saving      — disables Save while in-flight
 * @param {string}   saveError   — backend error message from save call
 * @param {boolean}  saved       — true once save succeeds (shows confirmation)
 * @param {function} onSave      — called when user clicks "Save scenario"
 */
export default function TcoResultsPanel({ result, saving, saveError, saved, onSave }) {
  const [showAssumptions, setShowAssumptions] = useState(false);

  return (
    <div className="flex flex-col gap-5">
      <TotalBadge total={result.total_5yr} />

      <Card title="Year-by-Year Breakdown">
        <div className="flex flex-col gap-5">
          <TcoChart data={result.year_by_year} />
          <YearByYearTable rows={result.year_by_year} />
        </div>
      </Card>

      {result.assumptions && result.assumptions.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowAssumptions((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-textMuted hover:text-text transition-colors duration-150 focus:outline-none"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`transition-transform duration-150 ${showAssumptions ? 'rotate-90' : ''}`}
              aria-hidden="true"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
            {showAssumptions ? 'Hide' : 'Show'} assumptions ({result.assumptions.length})
          </button>

          {showAssumptions && (
            <ul className="mt-2 space-y-1 pl-4">
              {result.assumptions.map((a, i) => (
                <li key={i} className="text-xs text-textMuted list-disc">
                  {a}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <WarningsBanner warnings={result.warnings} />

      <div className="flex flex-col gap-2">
        {saveError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
            <p className="text-sm text-red-400">{saveError}</p>
          </div>
        )}

        {saved ? (
          <div className="flex items-center gap-2 text-sm text-emerald-400">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M20 6 9 17l-5-5" />
            </svg>
            Scenario saved successfully.
          </div>
        ) : (
          <div className="flex items-center justify-end">
            <Button variant="primary" onClick={onSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save scenario'}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
