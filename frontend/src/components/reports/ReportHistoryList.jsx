import Card from '../ui/Card.jsx';

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Empty state when no reports have been generated yet */
function EmptyHistory() {
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-2">
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
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
      <p className="text-sm text-textMuted">No reports generated yet.</p>
      <p className="text-xs text-textMuted/60">Generate a PDF above to see it recorded here.</p>
    </div>
  );
}

/** Single report history row */
function ReportRow({ report }) {
  const artifactCount = report.included_artifacts?.length ?? 0;

  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-[var(--border)]/60 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text truncate">{report.title}</p>
        <p className="text-xs text-textMuted mt-0.5">
          {artifactCount} {artifactCount === 1 ? 'artifact' : 'artifacts'} &middot;{' '}
          {formatDate(report.created_at)}
        </p>
      </div>
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-textMuted/40 shrink-0"
        aria-hidden="true"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
    </div>
  );
}

/**
 * ReportHistoryList — previously generated reports for this project.
 *
 * @param {object[]} reports  — ReportRead[]
 * @param {boolean}  loading  — shows loading state while fetching
 * @param {string}   error    — error message if fetch failed
 */
export default function ReportHistoryList({ reports, loading, error }) {
  return (
    <Card title="Export History">
      {loading && (
        <div className="flex items-center justify-center py-8">
          <span className="text-sm text-textMuted">Loading history…</span>
        </div>
      )}

      {!loading && error && (
        <p className="text-sm text-red-400 py-4">{error}</p>
      )}

      {!loading && !error && reports.length === 0 && <EmptyHistory />}

      {!loading && !error && reports.length > 0 && (
        <div>
          {reports.map((r) => (
            <ReportRow key={r.id} report={r} />
          ))}
        </div>
      )}
    </Card>
  );
}
