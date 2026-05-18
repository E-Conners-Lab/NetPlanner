import Modal from '../ui/Modal.jsx';
import Button from '../ui/Button.jsx';

/**
 * ConfirmDialog — destructive-action confirmation built on Modal.
 *
 * @param {boolean}  open          — whether the dialog is visible
 * @param {function} onClose       — called when the user cancels or closes
 * @param {function} onConfirm     — called when the user confirms
 * @param {string}   [title]       — dialog heading (default: "Are you sure?")
 * @param {string}   [message]     — body message
 * @param {string}   [confirmLabel] — confirm button label (default: "Delete")
 * @param {boolean}  [submitting]  — disables buttons while async work is in flight
 * @param {string}   [error]       — error message shown if the action failed
 */
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  message = 'This action cannot be undone.',
  confirmLabel = 'Delete',
  submitting = false,
  error = null,
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-textMuted mb-6">{message}</p>

      {error && <p className="-mt-3 mb-5 text-sm text-red-400">{error}</p>}

      <div className="flex items-center justify-end gap-3">
        <Button variant="secondary" onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface bg-red-600 text-white hover:bg-red-500 active:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? 'Deleting…' : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
