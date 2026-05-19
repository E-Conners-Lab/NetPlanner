import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import useProject from '../hooks/useProject.js';
import { previewTco, saveTcoScenario, listTcoScenarios } from '../api/tco.js';
import Card from '../components/ui/Card.jsx';
import TcoInputForm from '../components/tco/TcoInputForm.jsx';
import TcoResultsPanel from '../components/tco/TcoResultsPanel.jsx';
import TcoSavedScenarios from '../components/tco/TcoSavedScenarios.jsx';

/** Extracts a user-facing message from an Axios error */
function extractErrorMessage(err, fallback) {
  return (
    err?.response?.data?.detail ||
    err?.response?.data?.message ||
    err?.message ||
    fallback
  );
}

export default function TCO() {
  const { id } = useParams();

  /* ── Project metadata ────────────────────────────────────────── */
  const { project, loading: projectLoading, error: projectError } = useProject(id);

  /* ── Preview state ───────────────────────────────────────────── */
  const [calculating, setCalculating] = useState(false);
  const [calcError, setCalcError] = useState(null);
  const [preview, setPreview] = useState(null);
  /* Cache the last submitted body so we can re-use it for save */
  const [lastBody, setLastBody] = useState(null);

  /* ── Save state ──────────────────────────────────────────────── */
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saved, setSaved] = useState(false);

  /* ── Saved scenarios state ───────────────────────────────────── */
  const [scenarios, setScenarios] = useState([]);
  const [scenariosLoading, setScenariosLoading] = useState(false);
  const [scenariosError, setScenariosError] = useState(null);

  /* ── Load saved scenarios ────────────────────────────────────── */
  const loadScenarios = useCallback(async () => {
    if (!id) return;

    setScenariosLoading(true);
    setScenariosError(null);

    try {
      const response = await listTcoScenarios(id);
      setScenarios(response.data);
    } catch (err) {
      setScenariosError(extractErrorMessage(err, 'Failed to load saved scenarios.'));
      setScenarios([]);
    } finally {
      setScenariosLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadScenarios();
  }, [loadScenarios]);

  /* ── Calculate (preview) ─────────────────────────────────────── */
  const handleCalculate = async (body) => {
    setCalculating(true);
    setCalcError(null);
    setPreview(null);
    setSaved(false);
    setSaveError(null);
    setLastBody(body);

    try {
      const response = await previewTco(id, body);
      setPreview(response.data);
    } catch (err) {
      setCalcError(extractErrorMessage(err, 'Failed to calculate TCO. Check your inputs and try again.'));
      setLastBody(null);
    } finally {
      setCalculating(false);
    }
  };

  /* ── Save scenario ───────────────────────────────────────────── */
  const handleSave = async () => {
    if (!lastBody) return;

    setSaving(true);
    setSaveError(null);

    try {
      await saveTcoScenario(id, lastBody);
      setSaved(true);
      await loadScenarios();
    } catch (err) {
      setSaveError(extractErrorMessage(err, 'Failed to save scenario. Please try again.'));
    } finally {
      setSaving(false);
    }
  };

  /* ── Project header ──────────────────────────────────────────── */
  const projectName = projectLoading
    ? 'Loading…'
    : projectError
      ? 'Unknown project'
      : project?.name ?? '';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-text">TCO Calculator</h1>
        <p className="mt-1 text-sm text-textMuted">
          Total cost of ownership modelling
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
      <Card title="Cost Inputs">
        <TcoInputForm onCalculate={handleCalculate} calculating={calculating} />

        {calcError && (
          <div className="mt-4 rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3">
            <p className="text-sm text-red-400">{calcError}</p>
          </div>
        )}
      </Card>

      {/* Results panel — only shown after a successful preview */}
      {preview && (
        <TcoResultsPanel
          result={preview}
          saving={saving}
          saveError={saveError}
          saved={saved}
          onSave={handleSave}
        />
      )}

      {/* Saved scenarios */}
      <TcoSavedScenarios
        scenarios={scenarios}
        loading={scenariosLoading}
        error={scenariosError}
      />
    </div>
  );
}
