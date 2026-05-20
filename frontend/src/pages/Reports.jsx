import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import useProject from '../hooks/useProject.js';
import { listTcoScenarios } from '../api/tco.js';
import { listComparisons } from '../api/comparison.js';
import {
  listConversations,
  generateReport,
  listReports,
  downloadReportPdf,
} from '../api/reports.js';
import Card from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
import Input from '../components/ui/Input.jsx';
import ArtifactSection from '../components/reports/ArtifactSection.jsx';
import ReportHistoryList from '../components/reports/ReportHistoryList.jsx';

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

/**
 * Slugify a title for use as a PDF filename.
 * e.g. "My Report 2026" -> "my-report-2026.pdf"
 */
function slugifyTitle(title) {
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'report'
  );
}

/**
 * Extracts a user-facing error message from an Axios error whose response
 * may be a Blob (because the request used responseType:'blob').
 *
 * When axios returns a blob-typed error body (e.g. a 422 from the reports
 * endpoint), err.response.data is a Blob, not a parsed object. We call
 * .text() on it to read the JSON string, then parse it to get `detail`.
 *
 * @param {Error} err      — Axios error
 * @param {string} fallback — shown when no detail can be parsed
 * @returns {Promise<string>}
 */
async function extractBlobErrorMessage(err, fallback) {
  if (!err?.response) {
    return err?.message || fallback;
  }

  const data = err.response.data;

  /* If the response data is a Blob, read it as text and try to parse JSON */
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text);
      if (parsed?.detail) return String(parsed.detail);
      if (parsed?.message) return String(parsed.message);
    } catch {
      /* fall through to generic message */
    }
  }

  /* Non-blob response: standard path */
  return (
    data?.detail ||
    data?.message ||
    err.message ||
    fallback
  );
}

/** Extracts a user-facing message from a standard (non-blob) Axios error */
function extractErrorMessage(err, fallback) {
  return (
    err?.response?.data?.detail ||
    err?.response?.data?.message ||
    err?.message ||
    fallback
  );
}

/**
 * Triggers a browser download for a PDF blob.
 * Prefers Content-Disposition filename from the response headers;
 * falls back to a slugified title.
 *
 * @param {Blob}   blob
 * @param {object} responseHeaders — axios response.headers
 * @param {string} title           — user-supplied report title
 */
function triggerPdfDownload(blob, responseHeaders, title) {
  const disposition = responseHeaders?.['content-disposition'] ?? '';
  let filename = `${slugifyTitle(title)}.pdf`;

  const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^;"'\s]+)["']?/i);
  if (filenameMatch && filenameMatch[1]) {
    filename = decodeURIComponent(filenameMatch[1]);
  }

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}

export default function Reports() {
  const { id } = useParams();

  /* ── Project metadata ────────────────────────────────────────── */
  const { project, loading: projectLoading, error: projectError } = useProject(id);

  /* ── Report title ────────────────────────────────────────────── */
  const [title, setTitle] = useState('');

  /* ── Artifact data ───────────────────────────────────────────── */
  const [scenarios, setScenarios] = useState([]);
  const [scenariosLoading, setScenariosLoading] = useState(false);
  const [scenariosError, setScenariosError] = useState(null);

  const [comparisons, setComparisons] = useState([]);
  const [comparisonsLoading, setComparisonsLoading] = useState(false);
  const [comparisonsError, setComparisonsError] = useState(null);

  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [conversationsError, setConversationsError] = useState(null);

  /* ── Artifact selection — immutable Set updates throughout ───── */
  const [selectedScenarioIds, setSelectedScenarioIds] = useState(new Set());
  const [selectedComparisonIds, setSelectedComparisonIds] = useState(new Set());
  const [selectedConversationIds, setSelectedConversationIds] = useState(new Set());

  /* ── Generation state ────────────────────────────────────────── */
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(null);

  /* ── Export history ──────────────────────────────────────────── */
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [reportsError, setReportsError] = useState(null);
  /* Per-row download state: id of the report currently downloading, and
   * an inline error specific to a history row (separate from the
   * generate-flow error so they don't overwrite each other). */
  const [downloadingReportId, setDownloadingReportId] = useState(null);
  const [reportsDownloadError, setReportsDownloadError] = useState(null);

  /* ── Load TCO scenarios ──────────────────────────────────────── */
  const loadScenarios = useCallback(async () => {
    if (!id) return;
    setScenariosLoading(true);
    setScenariosError(null);
    try {
      const response = await listTcoScenarios(id);
      setScenarios(response.data);
    } catch (err) {
      setScenariosError(extractErrorMessage(err, 'Failed to load TCO scenarios.'));
      setScenarios([]);
    } finally {
      setScenariosLoading(false);
    }
  }, [id]);

  /* ── Load comparisons ────────────────────────────────────────── */
  const loadComparisons = useCallback(async () => {
    if (!id) return;
    setComparisonsLoading(true);
    setComparisonsError(null);
    try {
      const response = await listComparisons(id);
      setComparisons(response.data);
    } catch (err) {
      setComparisonsError(extractErrorMessage(err, 'Failed to load vendor comparisons.'));
      setComparisons([]);
    } finally {
      setComparisonsLoading(false);
    }
  }, [id]);

  /* ── Load conversations ──────────────────────────────────────── */
  const loadConversations = useCallback(async () => {
    if (!id) return;
    setConversationsLoading(true);
    setConversationsError(null);
    try {
      const response = await listConversations(id);
      setConversations(response.data);
    } catch (err) {
      setConversationsError(extractErrorMessage(err, 'Failed to load advisor conversations.'));
      setConversations([]);
    } finally {
      setConversationsLoading(false);
    }
  }, [id]);

  /* ── Load export history ─────────────────────────────────────── */
  const loadReports = useCallback(async () => {
    if (!id) return;
    setReportsLoading(true);
    setReportsError(null);
    try {
      const response = await listReports(id);
      setReports(response.data);
    } catch (err) {
      setReportsError(extractErrorMessage(err, 'Failed to load export history.'));
      setReports([]);
    } finally {
      setReportsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadScenarios();
    loadComparisons();
    loadConversations();
    loadReports();
  }, [loadScenarios, loadComparisons, loadConversations, loadReports]);

  /* ── Immutable toggle helpers ────────────────────────────────── */
  const toggleScenario = useCallback((artifactId) => {
    setSelectedScenarioIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  }, []);

  const toggleComparison = useCallback((artifactId) => {
    setSelectedComparisonIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  }, []);

  const toggleConversation = useCallback((artifactId) => {
    setSelectedConversationIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  }, []);

  /* ── Derived: artifacts array for the POST body ──────────────── */
  const selectedArtifacts = [
    ...[...selectedScenarioIds].map((ref_id) => ({ kind: 'tco', ref_id })),
    ...[...selectedComparisonIds].map((ref_id) => ({ kind: 'comparison', ref_id })),
    ...[...selectedConversationIds].map((ref_id) => ({ kind: 'advisor_summary', ref_id })),
  ];

  const canGenerate = title.trim().length > 0 && selectedArtifacts.length > 0 && !generating;

  /* ── Generate PDF ────────────────────────────────────────────── */
  const handleGenerate = async () => {
    if (!canGenerate) return;

    setGenerating(true);
    setGenerateError(null);

    try {
      const response = await generateReport(id, {
        title: title.trim(),
        artifacts: selectedArtifacts,
      });

      triggerPdfDownload(response.data, response.headers, title.trim());

      /* Refresh the export history list immutably */
      await loadReports();
    } catch (err) {
      const message = await extractBlobErrorMessage(
        err,
        'Failed to generate report. Please try again.'
      );
      setGenerateError(message);
    } finally {
      setGenerating(false);
    }
  };

  /* ── Re-download a historical report ─────────────────────────── */
  const handleDownloadHistoryReport = async (report) => {
    if (downloadingReportId) return; // serialize clicks
    setDownloadingReportId(report.id);
    setReportsDownloadError(null);

    try {
      const response = await downloadReportPdf(id, report.id);
      triggerPdfDownload(response.data, response.headers, report.title);
    } catch (err) {
      const message = await extractBlobErrorMessage(
        err,
        'Failed to download this report. Please try again.'
      );
      setReportsDownloadError(message);
    } finally {
      setDownloadingReportId(null);
    }
  };

  /* ── Derived display values ──────────────────────────────────── */
  const projectName = projectLoading
    ? 'Loading…'
    : projectError
      ? 'Unknown project'
      : project?.name ?? '';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-text">Reports</h1>
        <p className="mt-1 text-sm text-textMuted">
          Generate and download PDF deliverables
          {projectName ? (
            <>
              {' for '}
              <span className="text-text font-medium">{projectName}</span>
            </>
          ) : null}
        </p>
      </div>

      {/* Project load error */}
      {projectError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
          <p className="text-sm text-red-400">{projectError.message}</p>
        </div>
      )}

      {/* Report builder card */}
      <Card title="Build Report">
        <div className="space-y-6">

          {/* Title input */}
          <Input
            label="Report title"
            id="report-title"
            placeholder="e.g. Q3 Network Modernisation Summary"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={generating}
          />

          {/* Artifact picker */}
          <div className="space-y-5">
            <p className="text-xs font-medium text-textMuted">
              Select artifacts to include (at least one required)
            </p>

            {/* TCO scenarios */}
            <ArtifactSection
              title="TCO Scenarios"
              items={scenarios}
              loading={scenariosLoading}
              error={scenariosError}
              emptyMessage="No saved TCO scenarios yet."
              selectedIds={selectedScenarioIds}
              onToggle={toggleScenario}
              renderLabel={(item) => (
                <span className="flex items-baseline justify-between gap-2 flex-wrap">
                  <span className="text-sm text-text font-medium">{item.scenario_name}</span>
                  <span className="font-mono text-xs text-accent tabular-nums shrink-0">
                    {USD.format(item.total_5yr)} 5yr
                  </span>
                </span>
              )}
            />

            {/* Vendor comparisons */}
            <ArtifactSection
              title="Vendor Comparisons"
              items={comparisons}
              loading={comparisonsLoading}
              error={comparisonsError}
              emptyMessage="No saved vendor comparisons yet."
              selectedIds={selectedComparisonIds}
              onToggle={toggleComparison}
              renderLabel={(item) => (
                <span className="flex items-baseline justify-between gap-2 flex-wrap">
                  <span className="text-sm text-text font-medium">
                    {item.vendors.join(' vs ')}
                  </span>
                  <span className="text-xs text-textMuted shrink-0">
                    {item.criteria.length}{' '}
                    {item.criteria.length === 1 ? 'criterion' : 'criteria'} &middot;{' '}
                    {formatDate(item.created_at)}
                  </span>
                </span>
              )}
            />

            {/* Advisor conversations */}
            <ArtifactSection
              title="Advisor Conversations"
              items={conversations}
              loading={conversationsLoading}
              error={conversationsError}
              emptyMessage="No advisor conversations yet."
              selectedIds={selectedConversationIds}
              onToggle={toggleConversation}
              renderLabel={(item) => (
                <span className="flex items-baseline justify-between gap-2 flex-wrap">
                  <span className="text-sm text-text font-medium truncate">{item.title}</span>
                  <span className="text-xs text-textMuted shrink-0">
                    {formatDate(item.created_at)}
                  </span>
                </span>
              )}
            />
          </div>

          {/* Selection summary */}
          {selectedArtifacts.length > 0 && (
            <p className="text-xs text-textMuted">
              {selectedArtifacts.length}{' '}
              {selectedArtifacts.length === 1 ? 'artifact' : 'artifacts'} selected
            </p>
          )}

          {/* Generation error */}
          {generateError && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
              <p className="text-sm text-red-400">{generateError}</p>
            </div>
          )}

          {/* Generate button */}
          <div className="flex items-center gap-3">
            <Button
              onClick={handleGenerate}
              disabled={!canGenerate}
            >
              {generating ? (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="animate-spin"
                    aria-hidden="true"
                  >
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  Generating…
                </>
              ) : (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <path d="M12 18v-6" />
                    <path d="m9 15 3 3 3-3" />
                  </svg>
                  Generate PDF
                </>
              )}
            </Button>

            {!canGenerate && !generating && (
              <p className="text-xs text-textMuted">
                {title.trim().length === 0 && selectedArtifacts.length === 0
                  ? 'Enter a title and select at least one artifact.'
                  : title.trim().length === 0
                    ? 'Enter a report title to continue.'
                    : 'Select at least one artifact to continue.'}
              </p>
            )}
          </div>
        </div>
      </Card>

      {/* Export history */}
      <ReportHistoryList
        reports={reports}
        loading={reportsLoading}
        error={reportsError}
        onDownload={handleDownloadHistoryReport}
        downloadingId={downloadingReportId}
        downloadError={reportsDownloadError}
      />
    </div>
  );
}
