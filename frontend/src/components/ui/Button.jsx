/**
 * Button — base interactive control.
 *
 * @param {'primary'|'secondary'} variant  — visual style
 * @param {boolean}               disabled
 * @param {React.ReactNode}       children
 * @param {function}              onClick
 * @param {string}                [className] — extra Tailwind classes
 * @param {'button'|'submit'|'reset'} [type]
 */
export default function Button({
  variant = 'primary',
  disabled = false,
  children,
  onClick,
  className = '',
  type = 'button',
  ...rest
}) {
  const base =
    'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:opacity-40 disabled:cursor-not-allowed';

  const variants = {
    primary:
      'bg-accent text-bg hover:bg-amber-400 active:bg-amber-600',
    secondary:
      'bg-surface text-text border border-[var(--border)] hover:border-textMuted active:bg-bg',
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={[base, variants[variant] ?? variants.primary, className].join(' ')}
      {...rest}
    >
      {children}
    </button>
  );
}
