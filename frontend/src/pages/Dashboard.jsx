import { useState } from 'react';
import useProjects from '../hooks/useProjects.js';
import { createProject } from '../api/projects.js';
import Button from '../components/ui/Button.jsx';
import Modal from '../components/ui/Modal.jsx';
import ProjectCard from '../components/projects/ProjectCard.jsx';
import ProjectForm from '../components/projects/ProjectForm.jsx';

/* ── Empty state ─────────────────────────────────────────────── */
function EmptyState({ onNew }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <svg
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-textMuted/30"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
      </svg>
      <div className="text-center">
        <p className="text-sm font-medium text-text">No projects yet</p>
        <p className="text-sm text-textMuted mt-1">Create your first one to get started.</p>
      </div>
      <Button variant="primary" onClick={onNew}>
        New Project
      </Button>
    </div>
  );
}

/* ── Error state ─────────────────────────────────────────────── */
function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <p className="text-sm text-red-400">{message}</p>
      <Button variant="secondary" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────── */
export default function Dashboard() {
  const { projects, loading, error, reload } = useProjects();
  const [showNewModal, setShowNewModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const openNew = () => {
    setSubmitError(null);
    setShowNewModal(true);
  };

  const closeNew = () => {
    if (submitting) return;
    setShowNewModal(false);
    setSubmitError(null);
  };

  const handleCreate = async (data) => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      await createProject(data);
      setShowNewModal(false);
      reload();
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to create project';
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">Dashboard</h1>
          <p className="mt-1 text-sm text-textMuted">
            Manage your network planning projects from one place.
          </p>
        </div>
        <Button variant="primary" onClick={openNew}>
          New Project
        </Button>
      </div>

      {/* Content area */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <span className="text-sm text-textMuted">Loading projects…</span>
        </div>
      )}

      {!loading && error && (
        <ErrorState message={error.message} onRetry={reload} />
      )}

      {!loading && !error && projects.length === 0 && (
        <EmptyState onNew={openNew} />
      )}

      {!loading && !error && projects.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {/* New project modal */}
      <Modal
        open={showNewModal}
        onClose={closeNew}
        title="New Project"
      >
        {submitError && (
          <p className="mb-4 text-sm text-red-400">{submitError}</p>
        )}
        <ProjectForm
          onSubmit={handleCreate}
          onCancel={closeNew}
          submitting={submitting}
        />
      </Modal>
    </div>
  );
}
