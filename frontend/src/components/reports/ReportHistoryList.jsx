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

function SpinnerIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="animate-spin text-accent shrink-0"
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-textMuted/60 group-hover:text-text shrink-0"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

/** Single report history row — click anywhere on the row to download. */
function ReportRow({ report, onDownload, downloading }) {
  const artifactCount = report.included_artifacts?.length ?? 0;
  const disabled = downloading || !onDownload;

  return (
    <button
      type="button"
      onClick={() => onDownload?.(report)}
      disabled={disabled}
      title={`Download "${report.title}"`}
      aria-label={`Download report ${report.title}`}
      className={[
        'group w-full flex items-center justify-between gap-4 py-3 px-3 -mx-3',
        'rounded-md text-left transition-colors',
        'border-b border-[var(--border)]/60 last:border-0',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        disabled
          ? 'opacity-60 cursor-default'
          : 'hover:bg-surface/60 active:bg-surface/80 cursor-pointer',
      ].join(' ')}
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text truncate">{report.title}</p>
        <p className="text-xs text-textMuted mt-0.5">
          {artifactCount} {artifactCount === 1 ? 'artifact' : 'artifacts'} &middot;{' '}
          {formatDate(report.created_at)}
        </p>
      </div>
      {downloading ? <SpinnerIcon /> : <DownloadIcon />}
    </button>
  );
}

/**
 * ReportHistoryList — previously generated reports for this project.
 *
 * @param {object[]} reports         — ReportRead[]
 * @param {boolean}  loading         — shows loading state while fetching
 * @param {string}   error           — error message if fetch failed
 * @param {function} [onDownload]    — invoked with the report when a row is clicked
 * @param {string}   [downloadingId] — id of the report currently being downloaded
 * @param {string}   [downloadError] — error from a failed download attempt
 */
export default function ReportHistoryList({
  reports,
  loading,
  error,
  onDownload,
  downloadingId,
  downloadError,
}) {
  return (
    <Card title="Export History">
      {loading && (
        <div className="flex items-center justify-center py-8">
          <span className="text-sm text-textMuted">Loading history…</span>
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {!loading && !error && reports.length === 0 && <EmptyHistory />}

      {!loading && !error && reports.length > 0 && (
        <>
          {downloadError && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3 mb-3">
              <p className="text-sm text-red-400">{downloadError}</p>
            </div>
          )}
          <div>
            {reports.map((r) => (
              <ReportRow
                key={r.id}
                report={r}
                onDownload={onDownload}
                downloading={r.id === downloadingId}
              />
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
