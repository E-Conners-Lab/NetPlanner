import { useState, useMemo } from 'react';
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

/* PID amendment 1.5 — version histories beyond this size collapse by default
 * so a noisy lineage never crowds the dashboard. */
const HISTORY_COLLAPSE_THRESHOLD = 5;

/** Group flat scenarios by lineage_id, latest version first inside each group. */
function groupByLineage(scenarios) {
  // Maintain newest-first dashboard order using the first scenario seen in each
  // lineage as the group's "creation" anchor (the list arrives newest-first).
  const groups = new Map();
  for (const scenario of scenarios) {
    const lineageId = scenario.lineage_id ?? scenario.id;
    if (!groups.has(lineageId)) {
      groups.set(lineageId, []);
    }
    groups.get(lineageId).push(scenario);
  }
  // Inside each group: highest version first (= the "latest" the user sees).
  return Array.from(groups.values()).map((rows) =>
    [...rows].sort((a, b) => (b.version ?? 1) - (a.version ?? 1))
  );
}

/** A single version row inside an expanded lineage. */
function VersionRow({ scenario, isLatest, isSelected, onSelect, onEdit }) {
  return (
    <div
      className={[
        'flex items-center justify-between gap-3 py-2 px-3 -mx-3',
        'rounded-md transition-colors',
        isSelected ? 'bg-accent/5' : 'hover:bg-surface/60',
      ].join(' ')}
    >
      <button
        type="button"
        onClick={() => onSelect?.(scenario)}
        className="flex-1 min-w-0 flex items-center justify-between gap-3 text-left focus:outline-none"
        aria-pressed={isSelected || undefined}
      >
        <div className="min-w-0 flex items-center gap-2">
          <span className="text-xs font-mono text-textMuted">v{scenario.version ?? 1}</span>
          {isLatest && (
            <span className="text-[10px] uppercase tracking-wide font-semibold px-1.5 py-0.5 rounded bg-accent/15 text-accent">
              latest
            </span>
          )}
          <span className="text-xs text-textMuted">{formatDate(scenario.created_at)}</span>
        </div>
        <span className="font-mono text-xs text-accent tabular-nums shrink-0">
          {USD.format(scenario.total_5yr)}
        </span>
      </button>
      {onEdit && (
        <button
          type="button"
          onClick={() => onEdit(scenario)}
          className="text-xs text-textMuted hover:text-text transition-colors duration-150 focus:outline-none px-2 py-1"
          aria-label={`Edit ${scenario.scenario_name} v${scenario.version ?? 1} as a new version`}
        >
          Edit
        </button>
      )}
    </div>
  );
}

/** A lineage card — header row + collapsible version history. */
function LineageGroup({ versions, onSelect, onEdit, selectedId }) {
  const latest = versions[0]; // versions is sorted highest version first
  const olderVersions = versions.slice(1);
  const isLargeHistory = versions.length > HISTORY_COLLAPSE_THRESHOLD;
  const [expanded, setExpanded] = useState(!isLargeHistory);

  return (
    <div className="border-b border-[var(--border)]/60 last:border-0 py-2">
      {/* Latest-version header (always visible) */}
      <div
        className={[
          'flex items-center justify-between gap-3 py-2 px-3 -mx-3 rounded-md transition-colors',
          selectedId === latest.id ? 'bg-accent/5' : 'hover:bg-surface/60',
        ].join(' ')}
      >
        <button
          type="button"
          onClick={() => onSelect?.(latest)}
          className="flex-1 min-w-0 flex items-center justify-between gap-4 text-left focus:outline-none"
          aria-pressed={selectedId === latest.id || undefined}
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-text truncate">{latest.scenario_name}</p>
              <span className="text-[10px] uppercase tracking-wide font-semibold px-1.5 py-0.5 rounded bg-accent/15 text-accent shrink-0">
                v{latest.version ?? 1}
              </span>
              {versions.length > 1 && (
                <span className="text-xs text-textMuted shrink-0">
                  · {versions.length} versions
                </span>
              )}
            </div>
            <p className="text-xs text-textMuted mt-0.5">{formatDate(latest.created_at)}</p>
          </div>
          <span className="font-mono text-sm font-semibold text-accent tabular-nums shrink-0">
            {USD.format(latest.total_5yr)}
          </span>
        </button>

        <div className="flex items-center gap-1 shrink-0">
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(latest)}
              className="text-xs text-textMuted hover:text-text transition-colors duration-150 focus:outline-none px-2 py-1"
              aria-label={`Edit ${latest.scenario_name} as a new version`}
            >
              Edit
            </button>
          )}
          {versions.length > 1 && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-xs text-textMuted hover:text-text transition-colors duration-150 focus:outline-none px-2 py-1"
              aria-expanded={expanded}
            >
              {expanded ? 'Hide history' : 'Show history'}
            </button>
          )}
        </div>
      </div>

      {/* Version history (collapsed by default for large lineages) */}
      {expanded && olderVersions.length > 0 && (
        <div className="mt-1 pl-4 border-l-2 border-[var(--border)]/40 ml-2">
          {olderVersions.map((version) => (
            <VersionRow
              key={version.id}
              scenario={version}
              isLatest={false}
              isSelected={version.id === selectedId}
              onSelect={onSelect}
              onEdit={onEdit}
            />
          ))}
        </div>
      )}
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
 * TcoSavedScenarios — list of previously saved TCO scenarios, grouped by
 * lineage (PID amendment 1.5). Each group shows the latest version; older
 * versions reveal on demand. Lineages with more than 5 versions collapse the
 * history by default to keep the dashboard quiet.
 *
 * @param {object[]} scenarios    — TCOScenarioRead[]
 * @param {boolean}  loading      — shows skeleton while fetching
 * @param {string}   error        — error message if fetch failed
 * @param {function} [onSelect]   — invoked with the scenario when a row is clicked
 * @param {string}   [selectedId] — id of the currently selected scenario, if any
 */
export default function TcoSavedScenarios({
  scenarios,
  loading,
  error,
  onSelect,
  onEdit,
  selectedId,
}) {
  const lineages = useMemo(() => groupByLineage(scenarios), [scenarios]);

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

      {!loading && !error && scenarios.length === 0 && <EmptyScenarios />}

      {!loading && !error && scenarios.length > 0 && (
        <div>
          {lineages.map((versions) => (
            <LineageGroup
              key={versions[0].lineage_id ?? versions[0].id}
              versions={versions}
              onSelect={onSelect}
              onEdit={onEdit}
              selectedId={selectedId}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
