import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import useProject from '../hooks/useProject.js';
import { generateComparison, listComparisons } from '../api/comparison.js';
import ComparisonForm from '../components/comparison/ComparisonForm.jsx';
import ComparisonMatrix from '../components/comparison/ComparisonMatrix.jsx';
import SavedComparisons from '../components/comparison/SavedComparisons.jsx';

/** Extracts a user-facing message from an Axios error */
function extractErrorMessage(err, fallback) {
  return (
    err?.response?.data?.detail ||
    err?.response?.data?.message ||
    err?.message ||
    fallback
  );
}

export default function Comparison() {
  const { id } = useParams();

  /* ── Project metadata ────────────────────────────────────────── */
  const { project, loading: projectLoading, error: projectError } = useProject(id);

  /* ── Generation state ────────────────────────────────────────── */
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);

  /* ── Currently displayed comparison (from generate or saved-row click) */
  const [activeComparison, setActiveComparison] = useState(null);

  /* ── Saved comparisons list ──────────────────────────────────── */
  const [comparisons, setComparisons] = useState([]);
  const [comparisonsLoading, setComparisonsLoading] = useState(false);
  const [comparisonsError, setComparisonsError] = useState(null);

  /* ── Load saved comparisons ──────────────────────────────────── */
  const loadComparisons = useCallback(async () => {
    if (!id) return;

    setComparisonsLoading(true);
    setComparisonsError(null);

    try {
      const response = await listComparisons(id);
      setComparisons(response.data);
    } catch (err) {
      setComparisonsError(extractErrorMessage(err, 'Failed to load saved comparisons.'));
      setComparisons([]);
    } finally {
      setComparisonsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadComparisons();
  }, [loadComparisons]);

  /* ── Generate comparison ─────────────────────────────────────── */
  const handleGenerate = async (body) => {
    setGenerating(true);
    setGenError(null);
    setActiveComparison(null);

    try {
      const response = await generateComparison(id, body);
      const result = response.data;
      setActiveComparison(result);
      /* Prepend to the saved list immutably */
      setComparisons((prev) => [result, ...prev]);
    } catch (err) {
      setGenError(
        extractErrorMessage(
          err,
          'Failed to generate comparison. Check your inputs and try again.'
        )
      );
    } finally {
      setGenerating(false);
    }
  };

  /* ── Select a saved comparison to display ────────────────────── */
  const handleSelectSaved = (comparison) => {
    setActiveComparison(comparison);
    setGenError(null);
  };

  /* ── Derived display values ──────────────────────────────────── */
  const projectName = projectLoading
    ? 'Loading…'
    : projectError
      ? 'Unknown project'
      : project?.name ?? '';

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-text">Vendor Comparison</h1>
        <p className="mt-1 text-sm text-textMuted">
          Side-by-side analysis across vendors and criteria
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

      {/* Input form */}
      <ComparisonForm onGenerate={handleGenerate} generating={generating} />

      {/* Generation error */}
      {genError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
          <p className="text-sm text-red-400">{genError}</p>
        </div>
      )}

      {/* Matrix — shown after successful generate or selecting a saved comparison */}
      {activeComparison && (
        <ComparisonMatrix comparison={activeComparison} />
      )}

      {/* Saved comparisons list */}
      <SavedComparisons
        comparisons={comparisons}
        loading={comparisonsLoading}
        error={comparisonsError}
        activeId={activeComparison?.id ?? null}
        onSelect={handleSelectSaved}
      />
    </div>
  );
}
