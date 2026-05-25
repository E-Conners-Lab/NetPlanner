import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import useProject from '../hooks/useProject.js';
import { previewTco, saveTcoScenario, listTcoScenarios } from '../api/tco.js';
import Card from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
import TcoInputForm from '../components/tco/TcoInputForm.jsx';
import TcoResultsPanel from '../components/tco/TcoResultsPanel.jsx';
import TcoSavedScenarios from '../components/tco/TcoSavedScenarios.jsx';
import TcoCompare from '../components/tco/TcoCompare.jsx';

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
  /* id of the currently-displayed saved scenario, if any — drives the
   * selected-row highlight in `TcoSavedScenarios`. */
  const [selectedScenarioId, setSelectedScenarioId] = useState(null);

  /* PID amendment 1.5 — when the user clicks "Edit as new version" on a saved
   * scenario, we pre-fill the form and remember the source scenario so the
   * next save submits with `parent_scenario_id`. */
  const [formInitial, setFormInitial] = useState(null);
  const [editingParent, setEditingParent] = useState(null);

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
    setSelectedScenarioId(null);

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

  /* ── Re-load a saved scenario into the results panel ─────────── */
  // No API call needed — the listing already carries everything the
  // results panel renders. `saved=true` + `lastBody=null` together gate
  // the Save button so a saved scenario can't be saved again.
  const handleSelectScenario = (scenario) => {
    setPreview(scenario);
    setSelectedScenarioId(scenario.id);
    setSaved(true);
    setSaveError(null);
    setCalcError(null);
    setLastBody(null);
  };

  /* PID amendment 1.5 — start editing a saved scenario as a new version. */
  const handleEditAsNewVersion = (scenario) => {
    setFormInitial(scenario);
    setEditingParent(scenario);
    setPreview(null);
    setSaved(false);
    setSaveError(null);
    setCalcError(null);
    setLastBody(null);
    setSelectedScenarioId(null);
    // Scroll the form into view so the user immediately sees the pre-fill.
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleCancelEdit = () => {
    setFormInitial(null);
    setEditingParent(null);
    setCalcError(null);
    setLastBody(null);
    setPreview(null);
  };

  /* ── Save scenario ───────────────────────────────────────────── */
  const handleSave = async () => {
    if (!lastBody) return;

    setSaving(true);
    setSaveError(null);

    try {
      const body = editingParent
        ? { ...lastBody, parent_scenario_id: editingParent.id }
        : lastBody;
      await saveTcoScenario(id, body);
      setSaved(true);
      setEditingParent(null);
      setFormInitial(null);
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

  /* Next-version label for the editing banner. We compute it from the
   * current saved-scenarios list so it stays accurate even if a sibling
   * version was just saved. */
  const nextVersion = editingParent
    ? Math.max(
        ...scenarios
          .filter((s) => (s.lineage_id ?? s.id) === editingParent.lineage_id)
          .map((s) => s.version ?? 1),
        editingParent.version ?? 1,
      ) + 1
    : null;

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

      {/* PID amendment 1.5 — editing-as-new-version banner */}
      {editingParent && (
        <div className="rounded-lg border border-accent/30 bg-accent/8 px-4 py-3 flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-text">
              Editing <span className="font-medium">{editingParent.scenario_name}</span>
              {' '}— saving creates{' '}
              <span className="font-mono text-accent">v{nextVersion}</span>{' '}
              in this lineage. The original is preserved.
            </p>
            <p className="text-xs text-textMuted mt-1">
              Form pre-filled from v{editingParent.version ?? 1}. Adjust any input below.
            </p>
          </div>
          <Button variant="secondary" onClick={handleCancelEdit} disabled={calculating || saving}>
            Cancel edit
          </Button>
        </div>
      )}

      {/* Input form */}
      <Card title={editingParent ? `Edit Inputs — v${editingParent.version ?? 1}` : 'Cost Inputs'}>
        <TcoInputForm
          key={editingParent?.id ?? 'fresh'}
          onCalculate={handleCalculate}
          calculating={calculating}
          initialValues={formInitial}
          submitLabel={editingParent ? 'Recalculate' : null}
        />

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
          saveLabel={editingParent ? `Save as v${nextVersion}` : 'Save scenario'}
        />
      )}

      {/* Saved scenarios */}
      <TcoSavedScenarios
        scenarios={scenarios}
        loading={scenariosLoading}
        error={scenariosError}
        onSelect={handleSelectScenario}
        onEdit={handleEditAsNewVersion}
        selectedId={selectedScenarioId}
      />

      {/* PID amendment 1.5 — screen-first comparison view */}
      <TcoCompare scenarios={scenarios} />
    </div>
  );
}
