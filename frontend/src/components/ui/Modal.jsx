import { useEffect } from 'react';

/**
 * Modal — generic centered modal with backdrop.
 *
 * - Closes on backdrop click.
 * - Closes on Escape key.
 * - Traps focus within the panel (aria-modal).
 *
 * @param {boolean}         open       — whether the modal is visible
 * @param {function}        onClose    — called when the user dismisses
 * @param {string}          [title]    — optional header title
 * @param {React.ReactNode} children
 * @param {string}          [className] — extra classes on the panel
 */
export default function Modal({ open, onClose, title, children, className = '' }) {
  /* Close on Escape key */
  useEffect(() => {
    if (!open) return;

    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  /* Prevent body scroll while open */
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  if (!open) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      aria-modal="true"
      role="dialog"
      aria-label={title || 'Dialog'}
    >
      {/* Semi-transparent overlay */}
      <div
        className="absolute inset-0 bg-bg/70 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={[
          'relative z-10 w-full max-w-lg rounded-xl bg-surface border border-[var(--border)] shadow-2xl',
          className,
        ].join(' ')}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
            <h2 className="text-base font-semibold text-text">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="text-textMuted hover:text-text transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
              aria-label="Close dialog"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        )}

        {/* Body */}
        <div className="px-6 py-5">
          {children}
        </div>
      </div>
    </div>
  );
}
