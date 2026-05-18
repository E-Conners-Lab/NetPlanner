/**
 * Card — surface-colored rounded panel.
 *
 * @param {string}          [title]     — optional header text
 * @param {React.ReactNode} children
 * @param {string}          [className] — additional Tailwind classes
 */
export default function Card({ title, children, className = '' }) {
  return (
    <div
      className={[
        'bg-surface rounded-xl border border-[var(--border)] overflow-hidden',
        className,
      ].join(' ')}
    >
      {title && (
        <div className="px-5 py-3 border-b border-[var(--border)]">
          <h2 className="text-sm font-semibold text-text">{title}</h2>
        </div>
      )}
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}
