import Card from '../ui/Card.jsx';

const USD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Single saved-scenario row */
function ScenarioRow({ scenario }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-[var(--border)]/60 last:border-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-text truncate">{scenario.scenario_name}</p>
        <p className="text-xs text-textMuted mt-0.5">{formatDate(scenario.created_at)}</p>
      </div>
      <span className="font-mono text-sm font-semibold text-accent tabular-nums shrink-0">
        {USD.format(scenario.total_5yr)}
      </span>
    </div>
  );
}

/** Empty state */
function EmptyScenarios() {
  return (
    <div className="flex flex-col items-center justify-center py-8 gap-2">
      <svg
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-textMuted/30"
        aria-hidden="true"
      >
        <rect x="4" y="2" width="16" height="20" rx="2" />
        <line x1="8" y1="6" x2="16" y2="6" />
        <line x1="8" y1="12" x2="16" y2="12" />
        <line x1="8" y1="18" x2="12" y2="18" />
      </svg>
      <p className="text-sm text-textMuted">No saved scenarios yet.</p>
      <p className="text-xs text-textMuted/60">Calculate and save a scenario above to see it here.</p>
    </div>
  );
}

/**
 * TcoSavedScenarios — list of previously saved TCO scenarios.
 *
 * @param {object[]} scenarios  — TCOScenarioRead[]
 * @param {boolean}  loading    — shows skeleton while fetching
 * @param {string}   error      — error message if fetch failed
 */
export default function TcoSavedScenarios({ scenarios, loading, error }) {
  return (
    <Card title="Saved Scenarios">
      {loading && (
        <div className="flex items-center justify-center py-8">
          <span className="text-sm text-textMuted">Loading scenarios…</span>
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {!loading && !error && scenarios.length === 0 && (
        <EmptyScenarios />
      )}

      {!loading && !error && scenarios.length > 0 && (
        <div>
          {scenarios.map((s) => (
            <ScenarioRow key={s.id} scenario={s} />
          ))}
        </div>
      )}
    </Card>
  );
}
