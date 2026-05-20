import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import useProject from '../hooks/useProject.js';
import { updateProject, deleteProject } from '../api/projects.js';
import Button from '../components/ui/Button.jsx';
import Card from '../components/ui/Card.jsx';
import Modal from '../components/ui/Modal.jsx';
import ConfirmDialog from '../components/shared/ConfirmDialog.jsx';
import ProjectForm from '../components/projects/ProjectForm.jsx';

/* ── Helpers ─────────────────────────────────────────────────── */
function formatBudget(value) {
  if (value == null) return 'No budget set';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso));
}

/* ── Field row ───────────────────────────────────────────────── */
function FieldRow({ label, value, mono = false }) {
  const isEmpty = value == null || value === '';
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-textMuted">{label}</span>
      <span
        className={[
          'text-sm',
          isEmpty ? 'text-textMuted/40 italic' : 'text-text',
          mono ? 'font-mono' : '',
        ].join(' ')}
      >
        {isEmpty ? 'Not provided' : value}
      </span>
    </div>
  );
}

/* ── Tool link card ──────────────────────────────────────────── */
function ToolCard({ to, icon, label, description }) {
  return (
    <Link
      to={to}
      className="group flex items-start gap-4 p-4 rounded-xl bg-surface border border-[var(--border)] hover:border-accent/40 transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
    >
      <div className="mt-0.5 text-textMuted group-hover:text-accent transition-colors duration-150">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-text group-hover:text-accent transition-colors duration-150">
          {label}
        </p>
        <p className="text-xs text-textMuted mt-0.5">{description}</p>
      </div>
    </Link>
  );
}

/* ── SVG icons ───────────────────────────────────────────────── */
function IconBot() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      <circle cx="9" cy="16" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="16" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
function IconCalculator() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <line x1="8" y1="6" x2="16" y2="6" />
      <line x1="8" y1="12" x2="16" y2="12" />
      <line x1="8" y1="18" x2="16" y2="18" />
      <line x1="12" y1="12" x2="12" y2="18" />
    </svg>
  );
}
function IconBarChart() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
      <line x1="2" y1="20" x2="22" y2="20" />
    </svg>
  );
}
function IconFileText() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

/* ── Main page ───────────────────────────────────────────────── */
export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { project, loading, error, reload } = useProject(id);

  const [showEdit, setShowEdit] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState(null);

  const [showDelete, setShowDelete] = useState(false);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  /* ── Edit handlers ─────────────────────────────────────────── */
  const openEdit = () => {
    setEditError(null);
    setShowEdit(true);
  };

  const closeEdit = () => {
    if (editSubmitting) return;
    setShowEdit(false);
    setEditError(null);
  };

  const handleEdit = async (data) => {
    setEditSubmitting(true);
    setEditError(null);

    try {
      await updateProject(id, data);
      setShowEdit(false);
      reload();
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to update project';
      setEditError(message);
    } finally {
      setEditSubmitting(false);
    }
  };

  /* ── Delete handlers ───────────────────────────────────────── */
  const openDelete = () => {
    setDeleteError(null);
    setShowDelete(true);
  };

  const closeDelete = () => {
    if (deleteSubmitting) return;
    setShowDelete(false);
    setDeleteError(null);
  };

  const handleDelete = async () => {
    setDeleteSubmitting(true);
    setDeleteError(null);

    try {
      await deleteProject(id);
      navigate('/');
    } catch (err) {
      /* Surface the failure and keep the dialog open so the user can retry. */
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to delete project';
      setDeleteError(message);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  /* ── Loading state ─────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="text-sm text-textMuted">Loading project…</span>
      </div>
    );
  }

  /* ── 404 / error state ─────────────────────────────────────── */
  if (error) {
    const isNotFound = error.status === 404;
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-sm font-medium text-text">
            {isNotFound ? 'Project not found' : 'Failed to load project'}
          </p>
          <p className="text-sm text-textMuted">
            {isNotFound
              ? 'This project may have been deleted or the link is incorrect.'
              : error.message}
          </p>
          <Link
            to="/"
            className="text-sm text-accent hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  /* ── Defensive guard (should not happen after loading + no error) */
  if (!project) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page header — the breadcrumb chain lives in the TopBar
          (Dashboard › Project Name); not duplicated here. */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-text truncate">{project.name}</h1>
          {project.company && (
            <p className="text-sm text-textMuted mt-0.5">{project.company}</p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button variant="secondary" onClick={openEdit}>
            Edit
          </Button>
          <button
            type="button"
            onClick={openDelete}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg text-red-400 border border-red-500/30 hover:bg-red-500/10 active:bg-red-500/20"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Project details */}
      <Card title="Project Details">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <FieldRow label="Description" value={project.description} />
          <FieldRow label="Budget Ceiling" value={formatBudget(project.budget_ceiling)} mono />
          <div className="sm:col-span-2">
            <FieldRow label="Existing Infrastructure" value={project.existing_infra} />
          </div>
          <FieldRow label="Created" value={formatDate(project.created_at)} mono />
          <FieldRow label="Last Updated" value={formatDate(project.updated_at)} mono />
          <FieldRow label="Project ID" value={project.id} mono />
        </div>
      </Card>

      {/* Tools section */}
      <div>
        <h2 className="text-base font-semibold text-text mb-3">Tools</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ToolCard
            to={`/projects/${id}/advisor`}
            icon={<IconBot />}
            label="AI Advisor"
            description="Get AI-powered vendor recommendations and network design advice."
          />
          <ToolCard
            to={`/projects/${id}/tco`}
            icon={<IconCalculator />}
            label="TCO Calculator"
            description="Model total cost of ownership across hardware, licensing, and ops."
          />
          <ToolCard
            to={`/projects/${id}/comparison`}
            icon={<IconBarChart />}
            label="Vendor Comparison"
            description="Compare shortlisted vendors side-by-side across key criteria."
          />
          <ToolCard
            to={`/projects/${id}/reports`}
            icon={<IconFileText />}
            label="Reports"
            description="Generate and export project reports for stakeholders."
          />
        </div>
      </div>

      {/* Edit modal */}
      <Modal open={showEdit} onClose={closeEdit} title="Edit Project">
        {editError && (
          <p className="mb-4 text-sm text-red-400">{editError}</p>
        )}
        <ProjectForm
          initialValues={project}
          onSubmit={handleEdit}
          onCancel={closeEdit}
          submitting={editSubmitting}
        />
      </Modal>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={showDelete}
        onClose={closeDelete}
        onConfirm={handleDelete}
        title="Delete Project"
        message={`"${project.name}" and all its data will be permanently deleted. This action cannot be undone.`}
        confirmLabel="Delete Project"
        submitting={deleteSubmitting}
        error={deleteError}
      />
    </div>
  );
}
