import Card from '../ui/Card.jsx';

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Empty state illustration */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-3">
      <svg
        width="36"
        height="36"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-textMuted/30"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
      <p className="text-sm text-textMuted">No saved comparisons yet.</p>
      <p className="text-xs text-textMuted/60">Generate a comparison above to see it saved here.</p>
    </div>
  );
}

/**
 * Single row for a saved comparison.
 *
 * @param {object}   comparison  — VendorComparisonRead
 * @param {boolean}  active      — whether this comparison is currently displayed
 * @param {function} onSelect    — called when the row is clicked
 */
function ComparisonRow({ comparison, active, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        'w-full text-left flex items-center justify-between gap-4 px-0 py-3',
        'border-b border-[var(--border)]/60 last:border-0',
        'transition-colors duration-100',
        'rounded hover:bg-bg/40',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset',
        active ? 'bg-bg/30' : '',
      ].join(' ')}
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text truncate">
          {comparison.vendors.join(' vs ')}
        </p>
        <p className="text-xs text-textMuted mt-0.5">
          {comparison.criteria.length} {comparison.criteria.length === 1 ? 'criterion' : 'criteria'} &middot;{' '}
          {formatDate(comparison.created_at)}
        </p>
      </div>

      {active && (
        <span className="shrink-0 text-xs font-medium text-accent">Viewing</span>
      )}
    </button>
  );
}

/**
 * SavedComparisons — lists previously generated comparisons; clicking one re-displays its matrix.
 *
 * @param {object[]}      comparisons       — VendorComparisonRead[]
 * @param {boolean}       loading           — shows loading state while fetching
 * @param {string|null}   error             — error message if fetch failed
 * @param {string|null}   activeId          — id of the currently displayed comparison
 * @param {function}      onSelect          — (comparison: VendorComparisonRead) => void
 */
export default function SavedComparisons({ comparisons, loading, error, activeId, onSelect }) {
  return (
    <Card title="Saved Comparisons">
      {loading && (
        <div className="flex items-center justify-center py-8">
          <span className="text-sm text-textMuted">Loading comparisons…</span>
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {!loading && !error && comparisons.length === 0 && <EmptyState />}

      {!loading && !error && comparisons.length > 0 && (
        <div>
          {comparisons.map((c) => (
            <ComparisonRow
              key={c.id}
              comparison={c}
              active={c.id === activeId}
              onSelect={() => onSelect(c)}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
